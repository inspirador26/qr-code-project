"""
GS1 DataBar Expanded Stacked rendering for AI(8112) serialized data strings.

Uses `zint-bindings` (PyPI: zint-bindings), a modern binding to libzint —
BSD-3-Clause, free for commercial/closed-source use, see the plan's "Barcode
library & licensing" section. Renders in-memory (no temp files) via
BARCODE_MEMORY_FILE, suitable for returning directly from a Django view.

Phase 0 spike notes (kept here deliberately — this took real debugging):
- `pyzint` (a different, older PyPI package) does NOT work for this: it has
  no GS1 input-mode flag and fails to encode any GS1 element string, even
  for a well-known AI unrelated to 8112. Don't reach for it.
- `zint-bindings` and the plain ctypes `zint` package both install a
  top-level module literally named `zint`, and collide if both are
  installed — only `zint-bindings` is a dependency here.
- zint's DataBar-family symbology names use the newer `DBAR_*` prefix
  (`DBAR_EXPSTK` = GS1 DataBar Expanded Stacked), not the legacy `RSS_*`
  names some older bindings/docs use for the same symbologies.
- Input must be GS1-AI-bracketed, e.g. `(8112)01003149314016714456765` —
  `InputMode.GS1PARENS` — not the raw digit string. zint validates AI(8112)'s
  internal VLI structure itself (confirmed via a deliberately malformed
  payload during the spike), which is a useful second layer of validation
  on top of gs1/data_string.py's own checks.
"""

import zint

from .data_string import AI


class BarcodeRenderError(RuntimeError):
    """Raised when zint fails to encode/render a data string."""


def render_gs1_databar_png(serialized_data_string: str) -> bytes:
    """Render an AI(8112) serialized data string as a GS1 DataBar Expanded
    Stacked PNG. No human-readable text is rendered alongside the barcode —
    the spec is deliberate about this for fraud mitigation (section 4.1).
    """
    if not serialized_data_string.startswith(AI):
        raise BarcodeRenderError(f"data string does not start with AI {AI}")

    # zint expects the AI in parens, with the rest of the digit string as
    # its value: "8112xxxxx" -> "(8112)xxxxx".
    gs1_input = f"({AI}){serialized_data_string[len(AI):]}"

    sym = zint.Symbol()
    sym.symbology = zint.Symbology.DBAR_EXPSTK
    sym.input_mode = zint.InputMode.GS1PARENS
    sym.show_hrt = False
    sym.output_options |= zint.OutputOptions.BARCODE_MEMORY_FILE
    sym.outfile = "barcode.png"  # extension selects PNG; never written to disk

    try:
        sym.encode(gs1_input)
        sym.print()
    except Exception as exc:  # zint raises plain Exception/RuntimeError with errtxt set
        raise BarcodeRenderError(f"failed to render {serialized_data_string!r}: {exc}") from exc

    return bytes(sym.memfile)
