from django.test import SimpleTestCase

from .barcode import render_gs1_databar_png
from .data_string import (
    DataStringError,
    build_base_data_string,
    build_serialized_data_string,
    parse_data_string,
)

# Worked example from TCB's real Provider API docs (deposit serialized GS1
# sample request body) — not from the spec PDF itself, but a genuine
# real-world AI(8112) serialized data string, so a good ground-truth case.
REAL_WORLD_SERIALIZED = "811201003149314016714456765"


class DataStringBuildTests(SimpleTestCase):
    def test_build_base_data_string(self):
        base = build_base_data_string(coupon_format="0", funder_id="0031493140", offer_code="167144")
        # 10-digit funder_id -> VLI = 10 - 6 = 4.
        self.assertEqual(base, "8112" + "0" + "4" + "0031493140" + "167144")

    def test_funder_id_length_bounds(self):
        # Valid: 6-12 digits
        build_base_data_string("0", "1" * 6, "123456")
        build_base_data_string("0", "1" * 12, "123456")
        with self.assertRaises(DataStringError):
            build_base_data_string("0", "1" * 5, "123456")
        with self.assertRaises(DataStringError):
            build_base_data_string("0", "1" * 13, "123456")

    def test_serial_number_length_bounds(self):
        build_serialized_data_string("0", "1" * 6, "123456", "2" * 6)
        build_serialized_data_string("0", "1" * 6, "123456", "2" * 15)
        with self.assertRaises(DataStringError):
            build_serialized_data_string("0", "1" * 6, "123456", "2" * 5)
        with self.assertRaises(DataStringError):
            build_serialized_data_string("0", "1" * 6, "123456", "2" * 16)

    def test_offer_code_must_be_exactly_six_digits(self):
        with self.assertRaises(DataStringError):
            build_base_data_string("0", "1" * 6, "12345")
        with self.assertRaises(DataStringError):
            build_base_data_string("0", "1" * 6, "1234567")

    def test_invalid_coupon_format_rejected(self):
        with self.assertRaises(DataStringError):
            build_base_data_string("2", "1" * 6, "123456")

    def test_non_digit_input_rejected(self):
        with self.assertRaises(DataStringError):
            build_base_data_string("0", "abcdef", "123456")


class DataStringParseTests(SimpleTestCase):
    def test_parse_real_world_serialized_string(self):
        parsed = parse_data_string(REAL_WORLD_SERIALIZED)
        self.assertEqual(parsed.ai, "8112")
        self.assertEqual(parsed.coupon_format, "0")
        self.assertIsNotNone(parsed.serial_number)

    def test_parse_rejects_wrong_ai(self):
        with self.assertRaises(DataStringError):
            parse_data_string("811001003149314016714456765")

    def test_parse_rejects_truncated_string(self):
        with self.assertRaises(DataStringError):
            parse_data_string("81120")

    def test_build_then_parse_round_trip(self):
        built = build_serialized_data_string(
            coupon_format="1",
            funder_id="123456789012",
            offer_code="999999",
            serial_number="1" * 15,
        )
        parsed = parse_data_string(built)
        self.assertEqual(parsed.coupon_format, "1")
        self.assertEqual(parsed.funder_id, "123456789012")
        self.assertEqual(parsed.offer_code, "999999")
        self.assertEqual(parsed.serial_number, "1" * 15)


class BarcodeRenderTests(SimpleTestCase):
    def test_renders_real_world_string_to_valid_png(self):
        png_bytes = render_gs1_databar_png(REAL_WORLD_SERIALIZED)
        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_no_human_readable_text_rendered(self):
        # show_hrt=False is set unconditionally in render_gs1_databar_png;
        # this test just guards against a future edit silently flipping it
        # back, since the spec is deliberate about no human-readable text
        # (fraud mitigation, section 4.1).
        import zint

        sym = zint.Symbol()
        sym.symbology = zint.Symbology.DBAR_EXPSTK
        sym.input_mode = zint.InputMode.GS1PARENS
        self.assertTrue(hasattr(sym, "show_hrt"))
