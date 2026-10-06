"""Load CMC lookup tables from the local, hash-pinned MAME reference.

Tables derive from MAME src/devices/bus/neogeo/prot_cmc.cpp, licensed
BSD-3-Clause, copyright S. Smith, David Haywood, Fabio Priuli. The full
license is tools/licenses/mame-pvc.txt (same holders and license).
No ROM data is embedded here. Run tools/fetch_reference.py if absent.
"""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = "src/devices/bus/neogeo/prot_cmc.cpp"


@lru_cache(maxsize=1)
def load_tables() -> dict:
    """Return name -> immutable 256-byte table; verify source before parsing."""
    manifest = json.loads((ROOT / "config/mame_sources.json").read_text())
    entries = [entry for entry in manifest["files"] if entry["path"] == SOURCE_PATH]
    if len(entries) != 1:
        raise ValueError("Expected exactly one pinned prot_cmc.cpp manifest entry")
    source = (ROOT / "artifacts/reference/prot_cmc.cpp").read_bytes()
    if hashlib.sha256(source).hexdigest() != entries[0]["sha256"]:
        raise ValueError("Reference source hash mismatch: " + SOURCE_PATH)
    source_text = source.decode("utf-8")
    tables = {}
    pattern = r"static\s+const\s+uint8_t\s+(\w+)\s*\[256\]\s*=\s*\{(.*?)\}\s*;"
    for name, body in re.findall(pattern, source_text, flags=re.DOTALL):
        # Strip comments before accepting only integer literal initializers.
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.DOTALL)
        tokens = [token.strip() for token in body.split(",") if token.strip()]
        if any(not re.fullmatch(r"0[xX][0-9a-fA-F]+|[0-9]+", token) for token in tokens):
            raise ValueError("Invalid table initializer: " + name)
        values = tuple(int(token, 16) if token.lower().startswith("0x") else int(token, 10)
                       for token in tokens)
        if name in tables or len(values) != 256 or any(value < 0 or value > 255 for value in values):
            raise ValueError("Invalid 256-byte table: " + name)
        tables[name] = values
    required = ["kof2000_" + suffix for suffix in
                ("type0_t03", "type0_t12", "type1_t03", "type1_t12",
                 "address_8_15_xor1", "address_8_15_xor2",
                 "address_16_23_xor1", "address_16_23_xor2", "address_0_7_xor")]
    required.extend(("m1_address_8_15_xor", "m1_address_0_7_xor"))
    if any(name not in tables for name in required):
        raise ValueError("Missing required CMC50 table")
    return tables
