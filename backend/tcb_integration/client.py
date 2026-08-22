"""
TCB (The Coupon Bureau) integration seam — the interface every part of the
app talks to, regardless of whether calls actually hit TCB's real API
(RealTcbClient) or a local stand-in (MockTcbClient, used until we have real
TCB credentials — see the plan's Open Item 1). Nothing outside this app
should import RealTcbClient/MockTcbClient directly; always go through
`get_tcb_client()` so swapping the backing implementation later is a
one-line settings change, not a refactor.

Endpoint shapes referenced in the docstrings below are grounded in TCB's
real Developer Portal (Manufacturer API v2.0,
portal.thecouponbureau.org/developer/api_docs) — see the plan's "TCB
integration seam" section for the full writeup.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DepositedItem:
    """One entry from a deposit_serials() response's `newly_added` bucket."""

    gs1: str
    valid_from: datetime | None = None
    valid_till: datetime | None = None
    campaign_metadata: dict = field(default_factory=dict)


@dataclass
class DepositResult:
    """The real /provider/deposit response is bucketed per item, not a
    single success/flag — see tcb_integration.models.TcbSyncLogClip, which
    exists specifically to record each item's bucket.
    """

    newly_added: list[DepositedItem] = field(default_factory=list)
    try_again: list[str] = field(default_factory=list)
    already_added: list[str] = field(default_factory=list)
    invalid_gs1s: list[str] = field(default_factory=list)
    no_copies_available: list[str] = field(default_factory=list)
    not_owned_by_you: list[str] = field(default_factory=list)
    not_yet_live: list[str] = field(default_factory=list)
    not_locked: list[str] = field(default_factory=list)
    expired: list[str] = field(default_factory=list)
    settled: list[str] = field(default_factory=list)
    metadata_not_set: list[str] = field(default_factory=list)
    client_txn_id: str = ""

    def bucket_for(self, gs1: str) -> str:
        for name in (
            "try_again",
            "already_added",
            "invalid_gs1s",
            "no_copies_available",
            "not_owned_by_you",
            "not_yet_live",
            "not_locked",
            "expired",
            "settled",
            "metadata_not_set",
        ):
            if gs1 in getattr(self, name):
                return name
        if any(item.gs1 == gs1 for item in self.newly_added):
            return "newly_added"
        return "unknown"


@dataclass
class RedemptionRecord:
    serialized_gs1: str
    base_gs1: str
    deposit_timestamp: str
    redeem_timestamp: str  # empty string means not (yet) redeemed
    provider: str = ""
    manufacturer: str = ""


class BaseTcbClient(ABC):
    """One instance per role would be more accurate to TCB's actual account
    model (Authorized Partner vs. Provider are separate credential sets —
    see the plan), but for now a single client exposes both roles' methods;
    split this up if/when that distinction becomes load-bearing.
    """

    @abstractmethod
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
        """POST /manufacturer_agent/base_gs1 — create or edit a Master Offer
        File. `update_mode`: 0=create (fails if base_gs1 exists), 1=edit.
        `lock=True` is required before any serial can be deposited against
        this MOF."""

    @abstractmethod
    def assign_provider(
        self, *, base_gs1: str, manufacturer_domain: str, provider_domain: str
    ) -> dict:
        """POST /manufacturer_agent/base_gs1/:base_gs1/toggle_provider — the
        actual authorization mechanism letting a Provider deposit against
        this MOF. Toggles: calling twice unassigns."""

    @abstractmethod
    def get_serialization_prefix(self) -> str:
        """GET /provider/serialization_prefix — every serial number we mint
        ourselves must start with this. Moot when using mode="base_gs1"."""

    @abstractmethod
    def deposit_serials(
        self,
        *,
        gs1s: list[str],
        mode: str | None = None,
        client_txn_id: str | None = None,
    ) -> DepositResult:
        """POST /provider/deposit — batches up to 20 per call. If
        mode="base_gs1", `gs1s` are base data strings and TCB generates+
        returns the randomized serial; otherwise `gs1s` are already-complete
        serialized data strings we generated ourselves."""

    @abstractmethod
    def create_fetch_code(
        self, *, gs1s: list[str], mode: str | None = None, validity_seconds: int | None = None
    ) -> dict:
        """POST /provider/time_bound_fetch_code — a short-lived PIN covering
        1-15 already-deposited serials, for POS-keypad/ecommerce redemption
        without scanning a barcode."""

    @abstractmethod
    def pull_audit_data(
        self,
        *,
        report_from_date: str | None = None,
        report_to_date: str | None = None,
        page_no: str | None = None,
        mode: str = "deposit",
    ) -> tuple[list[RedemptionRecord], str | None]:
        """GET /provider/data/fetch — polling, paginated. Returns
        (records, next_page_no); next_page_no is None when there are no more
        pages. mode="redemption" is what reporting.RedemptionEvent syncs
        from."""


def get_tcb_client() -> BaseTcbClient:
    """The one place the rest of the app should ask for a TCB client.
    Controlled by settings.TCB_USE_MOCK — flip that (not call sites) once
    real TCB credentials are provisioned. See the plan's Open Item 1.
    """
    from django.conf import settings

    if getattr(settings, "TCB_USE_MOCK", True):
        from .mock_client import MockTcbClient

        return MockTcbClient()

    from .real_client import RealTcbClient

    return RealTcbClient()
