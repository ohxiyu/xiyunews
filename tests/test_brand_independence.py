from pathlib import Path


ROOT = Path(__file__).parents[1]
VISIBLE_TEXT_ROOTS = (
    ROOT / ".github",
    ROOT / "docs",
    ROOT / "scripts",
    ROOT / "src",
)
VISIBLE_TEXT_FILES = (
    ROOT / "README.md",
    ROOT / "README_zh.md",
    ROOT / "README_ja.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "Dockerfile",
    ROOT / "docker-compose.yml",
    ROOT / "pyproject.toml",
)
TEXT_SUFFIXES = {
    ".html",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".yml",
}


def _visible_text_files() -> list[Path]:
    paths = list(VISIBLE_TEXT_FILES)
    for root in VISIBLE_TEXT_ROOTS:
        paths.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in TEXT_SUFFIXES
            and "_data" not in path.parts
            and "_posts" not in path.parts
        )
    return paths


def test_user_visible_project_surfaces_use_bmtnews_brand() -> None:
    leftovers = []
    for path in _visible_text_files():
        if "horizon" in path.read_text(encoding="utf-8").lower():
            leftovers.append(str(path.relative_to(ROOT)))

    assert leftovers == []


def test_brand_scan_covers_public_site_not_internal_resource_records() -> None:
    # Process documents audit exact legacy resource names and are not deployed.
    # Reader-facing docs, code, workflows and public README files stay covered.
    paths = _visible_text_files()
    assert ROOT / "README.md" in paths
    assert any(path.is_relative_to(ROOT / "docs") for path in paths)
    assert any(path.is_relative_to(ROOT / "src") for path in paths)
    assert any(path.is_relative_to(ROOT / ".github") for path in paths)
    assert not any(path.is_relative_to(ROOT / "project-docs") for path in paths)


def test_legal_files_separate_code_and_content_rights() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    content_rights = (ROOT / "CONTENT-LICENSE.md").read_text(encoding="utf-8")

    assert "Copyright (c) 2026 ohxiyu (BMTNews)" in license_text
    assert "Copyright (c) 2026 Thysrael" in license_text
    assert "Copyright (c) 2026 Thysrael" in notices
    assert "does not grant rights" in content_rights
    assert "third-party headlines" in content_rights
