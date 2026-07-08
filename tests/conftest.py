"""Make the spec package importable when the suite runs standalone (no install).

``uv run pytest`` inside ``spec/`` (or a plain ``pytest`` from the spec root)
must work in a fresh checkout of a future spec-only repository, so the accessor
package is put on ``sys.path`` directly rather than requiring an editable
install first.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
