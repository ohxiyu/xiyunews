"""Deployment-template contracts; no network, certificates or channel calls."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def servers(text: str) -> list[str]:
    blocks = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if lines[index] == "server {":
            start = index
            depth = 1
            index += 1
            while depth:
                depth += lines[index].count("{") - lines[index].count("}")
                index += 1
            blocks.append("\n".join(lines[start:index]))
        else:
            index += 1
    return blocks


def test_primary_and_transition_domains_keep_read_only_tls_proxy_contract():
    text = (ROOT / "realtime/scripts/deploy/nginx.conf").read_text()
    blocks = servers(text)
    for domain in ("api.xiyu.news", "api.fomobtc.com"):
        matching = [block for block in blocks if f"server_name {domain};" in block]
        assert len(matching) == 2
        http = next(block for block in matching if "listen 80;" in block)
        assert "location ^~ /.well-known/acme-challenge/" in http
        assert f"return 308 https://{domain}$request_uri;" in http
        tls = next(block for block in matching if "listen 443 ssl;" in block)
        assert f"/etc/letsencrypt/live/{domain}/fullchain.pem;" in tls
        assert f"/etc/letsencrypt/live/{domain}/privkey.pem;" in tls
        for directive in (
            "ssl_protocols TLSv1.2 TLSv1.3;",
            "limit_except GET OPTIONS { deny all; }",
            "limit_req zone=fomobtc_requests burst=20 nodelay;",
            "limit_conn fomobtc_clients 5;",
            "limit_conn fomobtc_total 80;",
            "proxy_pass http://127.0.0.1:8080;",
            "proxy_set_header X-Forwarded-For $remote_addr;",
            "add_header Cache-Control no-store always;",
            "location / { return 404; }",
        ):
            assert directive in tls
    assert text.count("limit_req_zone ") == 1
    assert text.count("server_name fomobtc.com www.fomobtc.com;") == 2
