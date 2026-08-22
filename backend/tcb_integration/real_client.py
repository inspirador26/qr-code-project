"""
Real HTTP implementation of BaseTcbClient, against TCB's actual Developer
Portal API (portal.thecouponbureau.org/developer/api_docs, Manufacturer API
v2.0). NOT YET EXERCISED against a live TCB account — we don't have
provisioned credentials yet (plan Open Item 1). Endpoint paths, headers, and
payload shapes below are transcribed directly from the real docs, but this
class should get a real smoke test against TCB's sandbox/live API the
moment credentials exist, before trusting it in Phase 2/3 flows.
"""

from datetime import datetime, timezone

import requests
from django.conf import settings
from django.core.cache import cache

from .client import BaseTcbClient, DepositedItem, DepositResult, RedemptionRecord
from .exceptions import TcbApiError, TcbConfigError

_TOKEN_CACHE_KEY_TMPL = "tcb_access_token:{role}"
_TOKEN_TTL_SECONDS = 23 * 60 * 60  # tokens are valid 24h; refresh a little early


class TcbRole:
    AUTHORIZED_PARTNER = "authorized_partner"
    PROVIDER = "provider"


def _credentials_for(role: str) -> tuple[str, str]:
    if role == TcbRole.AUTHORIZED_PARTNER:
        access_key = settings.TCB_AUTHORIZED_PARTNER_ACCESS_KEY
        secret_key = settings.TCB_AUTHORIZED_PARTNER_SECRET_KEY
    else:
        access_key = settings.TCB_PROVIDER_ACCESS_KEY
        secret_key = settings.TCB_PROVIDER_SECRET_KEY
    if not access_key or not secret_key:
        raise TcbConfigError(
            f"TCB {role} credentials are not configured — see .env.example. "
            "settings.TCB_USE_MOCK should stay True until these are set."
        )
    return access_key, secret_key


class RealTcbClient(BaseTcbClient):
    def __init__(self):
        self.base_url = settings.TCB_API_BASE_URL.rstrip("/")

    # -- auth -----------------------------------------------------------

    def _get_access_token(self, role: str) -> str:
        cache_key = _TOKEN_CACHE_KEY_TMPL.format(role=role)
        token = cache.get(cache_key)
        if token:
            return token

        access_key, secret_key = _credentials_for(role)
        resp = requests.post(
            f"{self.base_url}/access_token",
            headers={"Content-Type": "application/json", "x-api-key": access_key},
            json={"access_key": access_key, "secret_key": secret_key},
            timeout=15,
        )
        self._raise_for_tcb_error(resp)
        token = resp.json()["x-access-token"]
        cache.set(cache_key, token, timeout=_TOKEN_TTL_SECONDS)
        return token

    def _headers(self, role: str) -> dict:
        access_key, _ = _credentials_for(role)
        return {
            "Content-Type": "application/json",
            "x-api-key": access_key,
            "x-access-token": self._get_access_token(role),
        }

    @staticmethod
    def _raise_for_tcb_error(resp: requests.Response) -> None:
        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except ValueError:
                payload = {}
            raise TcbApiError(
                f"TCB API error {resp.status_code}: {payload.get('message', resp.text)}",
                status_code=resp.status_code,
                payload=payload,
            )

    # -- Authorized Partner role -----------------------------------------

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
        resp = requests.post(
            f"{self.base_url}/manufacturer_agent/base_gs1",
            headers=self._headers(TcbRole.AUTHORIZED_PARTNER),
            params={
                "email_domain": manufacturer_domain,
                "lock": "yes" if lock else "no",
            },
            json={
                "data": {
                    "base_gs1": base_gs1,
                    "update_mode": update_mode,
                    "brand_id": brand_id,
                    **mof_fields,
                }
            },
            timeout=30,
        )
        self._raise_for_tcb_error(resp)
        return resp.json()

    def assign_provider(
        self, *, base_gs1: str, manufacturer_domain: str, provider_domain: str
    ) -> dict:
        resp = requests.post(
            f"{self.base_url}/manufacturer_agent/base_gs1/{base_gs1}/toggle_provider",
            headers=self._headers(TcbRole.AUTHORIZED_PARTNER),
            params={"email_domain": manufacturer_domain},
            json={"email_domain": provider_domain},
            timeout=15,
        )
        self._raise_for_tcb_error(resp)
        return resp.json()

    # -- Provider role -----------------------------------------------------

    def get_serialization_prefix(self) -> str:
        resp = requests.get(
            f"{self.base_url}/provider/serialization_prefix",
            headers=self._headers(TcbRole.PROVIDER),
            timeout=15,
        )
        self._raise_for_tcb_error(resp)
        return resp.json()["prefix"]

    def deposit_serials(
        self,
        *,
        gs1s: list[str],
        mode: str | None = None,
        client_txn_id: str | None = None,
    ) -> DepositResult:
        if len(gs1s) > 20:
            raise TcbApiError(f"deposit_serials called with {len(gs1s)} items; TCB allows max 20 per call")

        body: dict = {"gs1s": gs1s}
        if mode:
            body["mode"] = mode
        if client_txn_id:
            body["client_txn_id"] = client_txn_id

        resp = requests.post(
            f"{self.base_url}/provider/deposit",
            headers=self._headers(TcbRole.PROVIDER),
            json=body,
            timeout=30,
        )
        self._raise_for_tcb_error(resp)
        payload = resp.json()

        return DepositResult(
            newly_added=[
                DepositedItem(
                    gs1=item["gs1"],
                    valid_from=_parse_epoch_ms(item.get("valid_from_timestamp")),
                    valid_till=_parse_epoch_ms(item.get("valid_till_timestamp")),
                    campaign_metadata=item.get("campaign_metadata", {}),
                )
                for item in payload.get("newly_added", [])
            ],
            try_again=payload.get("try_again", []),
            already_added=payload.get("already_added", []),
            invalid_gs1s=payload.get("invalid_gs1s", []),
            no_copies_available=payload.get("no_copies_available", []),
            not_owned_by_you=payload.get("not_owned_by_you", []),
            not_yet_live=payload.get("not_yet_live", []),
            not_locked=payload.get("not_locked", []),
            expired=payload.get("expired", []),
            settled=payload.get("settled", []),
            metadata_not_set=payload.get("metadata_not_set", []),
            client_txn_id=payload.get("client_txn_id", ""),
        )

    def create_fetch_code(
        self, *, gs1s: list[str], mode: str | None = None, validity_seconds: int | None = None
    ) -> dict:
        if len(gs1s) > 15:
            raise TcbApiError(f"create_fetch_code called with {len(gs1s)} items; TCB allows max 15")

        body: dict = {"gs1s": gs1s}
        if mode:
            body["mode"] = mode
        if validity_seconds is not None:
            body["validity_in_seconds"] = validity_seconds

        resp = requests.post(
            f"{self.base_url}/provider/time_bound_fetch_code",
            headers=self._headers(TcbRole.PROVIDER),
            json=body,
            timeout=30,
        )
        self._raise_for_tcb_error(resp)
        return resp.json()

    def pull_audit_data(
        self,
        *,
        report_from_date: str | None = None,
        report_to_date: str | None = None,
        page_no: str | None = None,
        mode: str = "deposit",
    ) -> tuple[list[RedemptionRecord], str | None]:
        params = {"mode": mode}
        if report_from_date:
            params["report_from_date"] = report_from_date
        if report_to_date:
            params["report_to_date"] = report_to_date
        if page_no:
            params["pageNo"] = page_no

        resp = requests.get(
            f"{self.base_url}/provider/data/fetch",
            headers=self._headers(TcbRole.PROVIDER),
            params=params,
            timeout=30,
        )
        self._raise_for_tcb_error(resp)
        payload = resp.json()

        records = [
            RedemptionRecord(
                serialized_gs1=row["serialized_gs1"],
                base_gs1=row["base_gs1"],
                deposit_timestamp=row.get("deposit_timestamp", ""),
                redeem_timestamp=row.get("redeem_timestamp", ""),
                provider=row.get("provider", ""),
                manufacturer=row.get("manufacturer", ""),
            )
            for row in payload.get("gs1s", [])
        ]
        next_page = payload.get("nextPageNo")
        if next_page in (None, "-1", -1):
            next_page = None
        return records, next_page


def _parse_epoch_ms(value) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
