"""
GS1 AI(8112) data-string builder/parser.

Implements the VLI (variable length indicator) encoding described in
`project-docs/AI (8112) Coupon Data SpecificationsV1.1.pdf`, section 3.1
("Required data string elements"):

    AI (8112, fixed)
    + Coupon Format      1 digit   (0 = digital, 1 = paper)
    + Coupon Funder VLI  1 digit   (actual length = VLI + 6; valid 0-6)
    + Coupon Funder ID   6-12 digits
    + Offer Code         6 digits
    + Serial Number VLI  1 digit   (actual length = VLI + 6; valid 0-9)
    + Serial Number      6-15 digits   (only present in the *serialized*
                                        data string, not the base one)

The "base data string" (AI + Format + Funder + Offer Code) is what TCB's
Create/Edit Master Offer File endpoint calls `base_gs1`. The "serialized
data string" (base + serial number) is what gets deposited per-clip and
rendered as the redemption barcode — see gs1/barcode.py and the plan's
"TCB integration seam" section.
"""

from dataclasses import dataclass

AI = "8112"

_FUNDER_VLI_OFFSET = 6
_FUNDER_VLI_MAX = 6  # valid VLI 0-6 -> length 6-12
_SERIAL_VLI_OFFSET = 6
_SERIAL_VLI_MAX = 9  # valid VLI 0-9 -> length 6-15


class DataStringError(ValueError):
    """Raised for any AI(8112) data string that fails spec validation."""


def _require_digits(value: str, field_name: str) -> None:
    if not value.isdigit():
        raise DataStringError(f"{field_name} must be digits only, got {value!r}")


def _encode_vli_field(value: str, field_name: str, offset: int, max_vli: int) -> str:
    _require_digits(value, field_name)
    length = len(value)
    vli = length - offset
    if not (0 <= vli <= max_vli):
        raise DataStringError(
            f"{field_name} length {length} is out of range "
            f"({offset}-{offset + max_vli} digits allowed)"
        )
    return f"{vli}{value}"


def build_base_data_string(coupon_format: str, funder_id: str, offer_code: str) -> str:
    """AI + Coupon Format + Coupon Funder ID (VLI-prefixed) + Offer Code.

    This is what TCB's Manufacturer/Authorized Partner API calls `base_gs1`.
    """
    if coupon_format not in ("0", "1"):
        raise DataStringError("coupon_format must be '0' (digital) or '1' (paper)")

    _require_digits(offer_code, "offer_code")
    if len(offer_code) != 6:
        raise DataStringError(f"offer_code must be exactly 6 digits, got {offer_code!r}")

    funder_field = _encode_vli_field(funder_id, "funder_id", _FUNDER_VLI_OFFSET, _FUNDER_VLI_MAX)

    base = f"{AI}{coupon_format}{funder_field}{offer_code}"
    if len(base) > 70:
        raise DataStringError(f"base data string exceeds 70 chars: {len(base)}")
    return base


def build_serialized_data_string(
    coupon_format: str, funder_id: str, offer_code: str, serial_number: str
) -> str:
    """base data string + Serial Number (VLI-prefixed). This is the payload
    deposited to TCB and encoded into the redemption barcode.
    """
    base = build_base_data_string(coupon_format, funder_id, offer_code)
    serial_field = _encode_vli_field(
        serial_number, "serial_number", _SERIAL_VLI_OFFSET, _SERIAL_VLI_MAX
    )
    serialized = f"{base}{serial_field}"
    if len(serialized) > 70:
        raise DataStringError(f"serialized data string exceeds 70 chars: {len(serialized)}")
    return serialized


@dataclass(frozen=True)
class ParsedDataString:
    ai: str
    coupon_format: str
    funder_id: str
    offer_code: str
    serial_number: str | None  # None for a base (unserialized) data string


def parse_data_string(data_string: str) -> ParsedDataString:
    """Decode a base or serialized AI(8112) data string. Raises
    DataStringError on any structural violation — this is deliberately
    strict, since a malformed string here means either our own encoding is
    wrong or (with untrusted input) a tampering attempt."""
    _require_digits(data_string, "data_string")

    def take(pos: int, n: int, field_name: str) -> tuple[str, int]:
        chunk = data_string[pos : pos + n]
        if len(chunk) != n:
            raise DataStringError(f"data string truncated in {field_name}")
        return chunk, pos + n

    if not data_string.startswith(AI):
        raise DataStringError(f"data string does not start with AI {AI}")
    pos = len(AI)

    coupon_format, pos = take(pos, 1, "coupon_format")
    if coupon_format not in ("0", "1"):
        raise DataStringError(f"invalid coupon_format digit: {coupon_format!r}")

    funder_vli_str, pos = take(pos, 1, "funder_vli")
    funder_len = int(funder_vli_str) + _FUNDER_VLI_OFFSET
    funder_id, pos = take(pos, funder_len, "funder_id")

    offer_code, pos = take(pos, 6, "offer_code")

    serial_number = None
    if pos < len(data_string):
        serial_vli_str, pos = take(pos, 1, "serial_vli")
        serial_len = int(serial_vli_str) + _SERIAL_VLI_OFFSET
        serial_number, pos = take(pos, serial_len, "serial_number")

    if pos != len(data_string):
        raise DataStringError("trailing data after expected fields")

    return ParsedDataString(
        ai=AI,
        coupon_format=coupon_format,
        funder_id=funder_id,
        offer_code=offer_code,
        serial_number=serial_number,
    )
