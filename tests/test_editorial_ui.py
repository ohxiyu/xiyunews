"""Guard the shared UI layer without changing published data semantics."""
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_editorial_layer_loads_after_reader_styles_and_is_versioned():
    head = (ROOT / 'docs/_includes/head-custom.html').read_text()
    assert head.index('editorial-ui.css') > head.index('pwa-reader.css')
    assert "'/assets/css/editorial-ui.css' | relative_url }}?v={{ site.asset_version }}" in head


def test_shared_reading_size_covers_lists_details_and_backgrounds():
    css = (ROOT / 'docs/assets/css/editorial-ui.css').read_text()
    for selector in ['.event-brief-block p', '.entity-feed-overview p',
                     '.entity-background p', '.event-current-state p',
                     '.event-update-change', '.story-more-content > section p',
                     '.weekly-brief-grid .event-brief-latest p']:
        assert selector in css
    assert 'font-size: var(--reading-size)' in css
    assert 'min-width: 1101px' in css
    assert '.section-index-body' in css


def test_production_templates_keep_evidence_and_details():
    archive = (ROOT / 'docs/_includes/archive-index.html').read_text() + (ROOT / 'docs/_includes/event-reading-context.html').read_text()
    weekly = (ROOT / 'docs/_includes/weekly-edition.html').read_text()
    for field in ['row.background_zh', 'row.discussion_zh', 'row.reference_links',
                  'row.recent_items', 'row.event_id']:
        assert field in archive
    assert 'why_it_matters' in weekly
    assert 'item.evidence' in weekly
    assert 'section-index-body' in archive and 'section-index-body' in weekly
    assert 'entity_background | escape' in archive


def test_beautiful_surface_preserves_reading_and_responsive_boundaries():
    css = (ROOT / 'docs/assets/css/editorial-ui.css').read_text()
    for token in ['--bg: #f5f6f8', '--surface: #ffffff', '--radius: 12px',
                  '--reading-size: 16px', '--detail-size: 13px',
                  '--reading-size: 15px', '--detail-size: 12.8px']:
        assert token in css
    for selector in ['.event-update', '.entity-card', '.weekly-history-list',
                     '.archive-row', '.story-more', '.share-card-preview canvas']:
        assert selector in css
    assert ':root[data-theme="dark"]' in css
    assert ':root:not([data-theme="light"])' in css
    assert '.story-summary-body { max-width: none; }' in css
    assert 'var(--control-radius)' in css
    assert ':focus-visible' in css
    assert '.event-update-rail time { white-space: nowrap; }' in css
    assert '.event-feed-compact .digest-item { padding: 9px 14px; }' in css
    reader = (ROOT / 'docs/assets/js/pwa-reader.js').read_text()
    assert 'Default text size: desktop 16px, mobile 15px' in reader
    assert '@import' not in css and 'url(' not in css
    # CSS cannot hide full news text, alter two-edition semantics or expose /s.
    # Only optional background is previewed, with an explicit expand control;
    # full news prose is never clamped and no-JS keeps all context readable.
    for rule in css.split('}'):
        if '-webkit-line-clamp:' in rule and '-webkit-line-clamp: unset' not in rule:
            assert '.story-summary-body' not in rule
    assert '.reading-context.is-enhanced [data-context-kind="background"]:not(.is-expanded)' in css
    controller = (ROOT / 'docs/assets/js/bmtnews-ui.js').read_text()
    assert '展开完整背景' in controller and "aria-expanded" in controller
    feed = (ROOT / 'docs/_includes/feed-home.html').read_text()
    assert 'for post in feed_posts limit:2' in feed
    layout = (ROOT / 'docs/_layouts/default.html').read_text()
    nav = layout.split('<nav\n          class="site-nav"', 1)[1].split('</nav>', 1)[0]
    assert '/s/' not in nav
