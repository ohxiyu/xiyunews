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
    assert (DOCS / "media-kit/logo-spec.md").read_bytes() == spec
    assert "186 − 162 = 24" in spec.decode()
    assert "G1" in spec.decode()
    # Entire foreground is within this rectangle; even its corners are safe.
    for x in (96, 416):
        for y in (26, 490):
            px, py = 102.4 + .6 * x, 102.4 + .6 * y
            assert (px - 256) ** 2 + (py - 256) ** 2 <= 204.8 ** 2


def test_old_versioned_assets_and_archives_remain_immutable():
    expected = {
        "v1": "4ba93771500535dd84a50a7f62359c3591c6c4c2c1ae4c8a1dc69e7158fbf87f",
        "v2": "93c5cc6daa5fd94f5f057d17aae171b710c802104f998e614289c91b529a3e01",
    }
    for version, digest in expected.items():
        path = DOCS / f"media-kit/bmtnews-media-kit-{version}.zip"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    with zipfile.ZipFile(DOCS / "media-kit/bmtnews-media-kit-v2.zip") as archive:
        for name in archive.namelist():
            if name.startswith("icons/bmtnews-"):
                assert archive.read(name) == (IMAGES / Path(name).name).read_bytes()


def test_generated_symbols_share_one_evenodd_master_and_exact_palette():
    master = ET.parse(ROOT / "brand/mark.svg").find("s:path", NS).attrib["d"]
    inline = ET.parse(DOCS / "_includes/brand-mark.html")
    assert inline.find("s:path", NS).attrib["d"] == master
    assert inline.getroot().attrib["aria-hidden"] == "true"
    master_parts = ET.parse(ROOT / "brand/mark.svg").findall("s:path", NS)
    assert len(master_parts) == 3
    assert [p.attrib["d"] for p in inline.findall("s:path", NS)] == [p.attrib["d"] for p in master_parts]
    assert master.count("A80 80") == 4
    assert master.count("A68 68") == 2
    assert master.count("A16 16") == 4
    for filename, color in [("blue", "#1d4c96"), ("dark", "#8fb0e6"),
                            ("black", "#1b1b18"), ("white", "#ffffff")]:
        path = ET.parse(DOCS / f"media-kit/bmtnews-mark-{filename}.svg").find("s:path", NS)
        assert path.attrib["d"] == master
        assert path.attrib["fill-rule"] == "evenodd"
        assert path.attrib["fill"] == color
        parts = ET.parse(DOCS / f"media-kit/bmtnews-mark-{filename}.svg").findall("s:path", NS)
        assert [p.attrib["d"] for p in parts] == [p.attrib["d"] for p in master_parts]
        assert parts[1].attrib["fill"] == ("none" if filename in {"black", "white"} else "#ffcc29")
        assert parts[2].attrib["fill"] == color
    for path in (DOCS / "media-kit").glob("*.svg"):
        text = path.read_text()
        assert "<text" not in text, "Media wordmarks must not depend on installed fonts"
        assert "Gradient" not in text and "<image" not in text and "<script" not in text


def test_pwa_uses_versioned_distinct_maskable_and_any_icons():
    manifest = json.loads((DOCS / "manifest.webmanifest").read_text())
    assert manifest["id"] == "/"  # Never create a new installed-app identity.
    by_purpose = {icon["purpose"]: icon for icon in manifest["icons"]}
    assert by_purpose["maskable"]["src"] != by_purpose["any"]["src"]
    for icon in manifest["icons"]:
        assert "-v3.png" in icon["src"]
        data = (DOCS / icon["src"].lstrip("/")).read_bytes()
        width, height = struct.unpack(">II", data[16:24])
        assert f"{width}x{height}" == icon["sizes"]
    masked = ET.parse(DOCS / "media-kit/bmtnews-maskable.svg")
    for name in ("app", "apple", "maskable"):
        app = ET.parse(DOCS / f"media-kit/bmtnews-{name}.svg")
        assert app.findall("s:path", NS)[2].attrib["fill"] == "#1d4c96"
    assert masked.find("s:rect", NS).attrib.get("rx", "0") == "0"
    assert masked.find("s:path", NS).attrib["transform"] == "translate(102.4 102.4) scale(.6)"
    assert struct.unpack(">II", (IMAGES / "bmtnews-apple-180-v3.png").read_bytes()[16:24]) == (180, 180)


def test_media_archive_is_complete_and_matches_committed_assets():
    with zipfile.ZipFile(DOCS / "media-kit/bmtnews-media-kit-v3.zip") as archive:
        assert archive.testzip() is None
        assert "README.md" in archive.namelist()
        assert "source/mark.svg" in archive.namelist()
        for path in (DOCS / "media-kit").iterdir():
            if path.suffix in {".svg", ".png", ".md"}:
                assert archive.read(path.name) == path.read_bytes()
        for path in IMAGES.glob("bmtnews-*v3.*"):
            assert archive.read("icons/" + path.name) == path.read_bytes()
        for path in (ROOT / "brand").iterdir():
            if path.is_file():
                assert archive.read("source/" + path.name) == path.read_bytes()


def test_headers_sharing_and_favicons_use_the_new_brand():
    layout = (DOCS / "_layouts/default.html").read_text()
    head = (DOCS / "_includes/head-custom.html").read_text()
    assert layout.count("include brand-mark.html") == 2  # Header + footer
    assert "bmtnews-social-v3.png" in layout
    assert "bmtnews-favicon-v3.svg" in head
    assert "bmtnews-apple-180-v3.png" in head
    assert "?v=brand-20261001" in head
    assert "media-kit/" in layout
    assert struct.unpack(">II", (IMAGES / "bmtnews-social-v3.png").read_bytes()[16:24]) == (1200, 630)
    assert struct.unpack("<HHH", (DOCS / "favicon.ico").read_bytes()[:6]) == (0, 1, 3)
    css = (DOCS / "assets/css/bmtnews-ui.css").read_text()
    assert "color: var(--accent)" in css.split(".site-brand-mark {", 1)[1].split("}", 1)[0]
    card = (DOCS / "assets/js/story-card.js").read_text()
    assert ".site-brand .site-brand-mark path" in card
    assert "new Path2D(mark.getAttribute('d'))" in card
    assert "marks.forEach" in card  # Canvas must include eye and pupil, not only body.
