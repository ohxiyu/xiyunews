"""Root documentation pruning must preserve links from the independent app."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_shared_realtime_document_addresses_keep_immutable_archive_targets():
    for name in ('cloudflare-single-project.md','realtime-server-migration.md',
                 'releases/2026-10-05-realtime-api-domain.md',
                 'releases/2026-10-03-cloudflare-production-verification.md'):
        text=(ROOT/'project-docs'/name).read_text()
        assert len(text)<650
        assert '/blob/81a57092df0c4e43249516ecedbb907ee8b8d2fb/project-docs/'+name in text
        assert 'daily-dispatcher.md' in text
