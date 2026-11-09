"""Brand identity and packaged-asset regression checks (stdlib only)."""
import json
import hashlib
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
IMAGES = DOCS / "assets/images"
NS = {"s": "http://www.w3.org/2000/svg"}


def test_v3_master_matches_documented_exact_geometry():
    parts = ET.parse(ROOT / "brand/mark.svg").findall("s:path", NS)
    head = "M292 94A68 68 0 1 0 156 94A68 68 0 1 0 292 94Z"
    body = ("M176 186H336A80 80 0 0 1 416 266V410A80 80 0 0 1 336 490"
            "H176A80 80 0 0 1 96 410V266A80 80 0 0 1 176 186Z")
    slot = ("M156 340H248A16 16 0 0 1 264 356A16 16 0 0 1 248 372"
            "H156A16 16 0 0 1 140 356A16 16 0 0 1 156 340Z")
    outer = "M378 264A36 36 0 1 0 306 264A36 36 0 1 0 378 264Z"
    inner = "M354 264A12 12 0 1 0 330 264A12 12 0 1 0 354 264Z"
    assert [p.attrib["id"] for p in parts] == ["body", "eye", "pupil"]
    assert [p.attrib["d"] for p in parts] == [head + body + slot + outer, outer + inner, inner]
    assert parts[2].attrib["fill"] == "currentColor"
    spec = (ROOT / "brand/logo-spec.md").read_bytes()
    assert "186 − 162 = 24" in spec.decode()
    assert "G1" in spec.decode()
    # Entire foreground is within this rectangle; even its corners are safe.
    for x in (96, 416):
        for y in (26, 490):
            px, py = 102.4 + .6 * x, 102.4 + .6 * y
            assert (px - 256) ** 2 + (py - 256) ** 2 <= 204.8 ** 2












def test_deployed_robot_uses_the_original_master():
    master=ET.parse(ROOT / "brand/mark.svg").findall("s:path", NS)
    inline=ET.parse(DOCS / "_includes/brand-mark.html")
    assert [p.attrib["d"] for p in inline.findall("s:path",NS)] == [p.attrib["d"] for p in master]
    assert inline.getroot().attrib["aria-hidden"] == "true"
    assert len(master)==3
    assert "brand-mark.html" in (DOCS / "_includes/core-layout.html").read_text()
