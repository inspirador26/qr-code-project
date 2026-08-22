"""
In-memory stand-in for TCB's real API, implementing the same BaseTcbClient
interface as RealTcbClient — everything in the app should be able to call
into this without knowing it isn't the real thing, and swap to
RealTcbClient later purely via settings.TCB_USE_MOCK. See the plan's Open
Item 1: we don't have real TCB credentials yet, so this is what
`get_tcb_client()` returns by default.

State is process-local (class-level dicts) and NOT persisted anywhere —
restarting the dev server / test process resets it. That's intentional:
this is a test double, not a second production data store. Mirrors the
real API's documented behavior closely enough to exercise the actual
offer -> lock -> deposit -> (simulated) redemption flow end to end,
including the interesting failure buckets (not_locked, no_copies_available,
not_owned_by_you, already_added) — not just the happy path.
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from django.conf import settings

from gs1.data_string import build_serialized_data_string, parse_data_string

from .client import BaseTcbClient, DepositedItem, DepositResult, RedemptionRecord
from .exceptions import TcbApiError

MOCK_SERIALIZATION_PREFIX = "9"  # arbitrary — must be a single digit here since
# our shortest allowed serial_number length is 6 digits and we pad the rest
# randomly; a real prefix from TCB could be longer.


@dataclass
class _MockMof:
    base_gs1: str
    manufacturer_domain: str
    brand_id: str
    locked: bool = False
    total_circulation: int = 0
    deposited_count: int = 0
    authorized_providers: set = field(default_factory=set)
    mof_fields: dict = field(default_factory=dict)


class MockTcbClient(BaseTcbClient):
    # Class-level so state survives across `MockTcbClient()` instantiations
    # within a process (services.py creates a fresh instance per call).
    _mofs: dict[str, _MockMof] = {}
    _deposited: dict[str, dict] = {}  # serialized_gs1 -> {base_gs1, deposited_at, redeemed_at}
    _fetch_codes: dict[str, list[str]] = {}

    @classmethod
    def reset(cls):
        """Test-only: clear all mock state between test cases."""
        cls._mofs.clear()
        cls._deposited.clear()
        cls._fetch_codes.clear()

    @classmethod
    def simulate_redemption(cls, serialized_gs1: str, *, redeemed_at: datetime | None = None) -> None:
        """Test/dev-only helper with no real-TCB equivalent: marks a
        deposited serial as redeemed, so pull_audit_data(mode="redemption")
        has something to report back — lets us exercise the
        reporting.RedemptionEvent reconciliation path without a real POS.
        """
        record = cls._deposited.get(serialized_gs1)
        if record is None:
            raise TcbApiError(f"{serialized_gs1} was never deposited in the mock")
        record["redeemed_at"] = redeemed_at or datetime.now(timezone.utc)

    def register_offer(
        self,
        *,
        base_gs1: str,
        manufacturer_domain: str,
        brand_id: str,
        update_mode: int,
        lock: bool,
        mof_fields: dict,
    ) -> dict:
        existing = self._mofs.get(base_gs1)
        if update_mode == 0 and existing is not None:
            raise TcbApiError(f"base_gs1 {base_gs1} already exists (update_mode=0 requires create)")
        if update_mode == 1 and existing is None:
            raise TcbApiError(f"base_gs1 {base_gs1} does not exist (update_mode=1 requires edit)")

        total_circulation = int(mof_fields.get("total_circulation", 0) or 0)
        if existing and total_circulation < existing.deposited_count:
            raise TcbApiError(
                f"total_circulation {total_circulation} cannot be lowered below "
                f"current deposit count {existing.deposited_count}"
            )

        mof = existing or _MockMof(
            base_gs1=base_gs1, manufacturer_domain=manufacturer_domain, brand_id=brand_id
        )
        mof.total_circulation = total_circulation
        mof.mof_fields = mof_fields
        if lock:
            mof.locked = True
        self._mofs[base_gs1] = mof

        return {"status": "success", "message": "Successfully created" if not existing else "Successfully updated"}

    def assign_provider(
        self, *, base_gs1: str, manufacturer_domain: str, provider_domain: str
    ) -> dict:
        mof = self._mofs.get(base_gs1)
        if mof is None:
            raise TcbApiError(f"base_gs1 {base_gs1} not found")

        if provider_domain in mof.authorized_providers:
            mof.authorized_providers.discard(provider_domain)
            action = "deleted"
        else:
            mof.authorized_providers.add(provider_domain)
            action = "assigned"

        return {"status": "success", "message": f"Successfully {action}", "action": action}

    def get_serialization_prefix(self) -> str:
        return MOCK_SERIALIZATION_PREFIX

    def deposit_serials(
        self,
        *,
        gs1s: list[str],
        mode: str | None = None,
        client_txn_id: str | None = None,
    ) -> DepositResult:
        if len(gs1s) > 20:
            raise TcbApiError(f"deposit_serials called with {len(gs1s)} items; TCB allows max 20 per call")

        provider_domain = getattr(settings, "TCB_PLATFORM_EMAIL_DOMAIN", "")
        result = DepositResult(client_txn_id=client_txn_id or "")

        for item in gs1s:
            base_gs1 = item if mode == "base_gs1" else _base_gs1_of(item)
            mof = self._mofs.get(base_gs1)

            if mof is None:
                result.invalid_gs1s.append(item)
                continue
            if provider_domain not in mof.authorized_providers:
                result.not_owned_by_you.append(item)
                continue
            if not mof.locked:
                result.not_locked.append(item)
                continue
            if mof.deposited_count >= mof.total_circulation:
                result.no_copies_available.append(item)
                continue

            if mode == "base_gs1":
                serialized_gs1 = _generate_serial(base_gs1)
            else:
                serialized_gs1 = item
                if serialized_gs1 in self._deposited:
                    result.already_added.append(item)
                    continue

            now = datetime.now(timezone.utc)
            valid_till = now + timedelta(days=90)  # mock default; real validity comes from the MOF
            self._deposited[serialized_gs1] = {
                "base_gs1": base_gs1,
                "deposited_at": now,
                "redeemed_at": None,
                "valid_till": valid_till,
            }
            mof.deposited_count += 1
            result.newly_added.append(
                DepositedItem(gs1=serialized_gs1, valid_from=now, valid_till=valid_till)
            )

        return result

    def create_fetch_code(
        self, *, gs1s: list[str], mode: str | None = None, validity_seconds: int | None = None
    ) -> dict:
        if len(gs1s) > 15:
            raise TcbApiError(f"create_fetch_code called with {len(gs1s)} items; TCB allows max 15")

        valid_gs1s = [g for g in gs1s if g in self._deposited]
        unauthorized_gs1s = [g for g in gs1s if g not in self._deposited]

        if not valid_gs1s:
            return {"status": "error", "valid_gs1s": [], "unauthorized_gs1s": unauthorized_gs1s}

        fetch_code = f"MOCK{secrets.randbelow(10**8):08d}"
        self._fetch_codes[fetch_code] = valid_gs1s

        return {
            "status": "success",
            "valid_gs1s": valid_gs1s,
            "unauthorized_gs1s": unauthorized_gs1s,
            "fetch_code": fetch_code,
        }

    def pull_audit_data(
        self,
        *,
        report_from_date: str | None = None,
        report_to_date: str | None = None,
        page_no: str | None = None,
        mode: str = "deposit",
    ) -> tuple[list[RedemptionRecord], str | None]:
        records = []
        for serialized_gs1, info in self._deposited.items():
            if mode == "redemption" and info["redeemed_at"] is None:
                continue
            records.append(
                RedemptionRecord(
                    serialized_gs1=serialized_gs1,
                    base_gs1=info["base_gs1"],
                    deposit_timestamp=info["deposited_at"].isoformat(),
                    redeem_timestamp=info["redeemed_at"].isoformat() if info["redeemed_at"] else "",
                )
            )
        return records, None  # mock never paginates


def _base_gs1_of(serialized_or_base: str) -> str:
    """A base_gs1 has no serial number segment; a serialized one does.
    parse_data_string tells us which we were given."""
    parsed = parse_data_string(serialized_or_base)
    if parsed.serial_number is None:
        return serialized_or_base
    return _strip_serial(serialized_or_base, parsed)


def _strip_serial(serialized: str, parsed) -> str:
    serial_field_len = 1 + len(parsed.serial_number)  # VLI digit + serial digits
    return serialized[: len(serialized) - serial_field_len]


def _generate_serial(base_gs1: str) -> str:
    parsed = parse_data_string(base_gs1)
    # Mock serial: our fake prefix + random digits, within the 6-15 digit
    # spec range (see gs1.data_string). Retries on the (extremely unlikely)
    # chance of a collision within this base_gs1.
    for _ in range(10):
        suffix_len = 8
        suffix = "".join(str(secrets.randbelow(10)) for _ in range(suffix_len))
        serial_number = f"{MOCK_SERIALIZATION_PREFIX}{suffix}"
        candidate = build_serialized_data_string(
            coupon_format=parsed.coupon_format,
            funder_id=parsed.funder_id,
            offer_code=parsed.offer_code,
            serial_number=serial_number,
        )
        if candidate not in MockTcbClient._deposited:
            return candidate
    raise TcbApiError("mock serial generation collided 10 times in a row — did you fix a seed?")
