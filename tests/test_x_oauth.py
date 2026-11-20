"""OAuth signing retains the established deterministic signature contract."""
from src.services.x_delivery import _oauth_header

def test_oauth_header_is_deterministic_and_signed() -> None:
    header = _oauth_header(
        "POST",
        "https://api.x.com/2/tweets",
        consumer_key="ck",
        consumer_secret="cs",
        access_token="at",
        access_secret="as",
        nonce="fixednonce",
        timestamp="1700000000",
    )
    again = _oauth_header(
        "POST",
        "https://api.x.com/2/tweets",
        consumer_key="ck",
        consumer_secret="cs",
        access_token="at",
        access_secret="as",
        nonce="fixednonce",
        timestamp="1700000000",
    )
    assert header == again
    assert header.startswith("OAuth ")
    assert 'oauth_signature_method="HMAC-SHA1"' in header
    assert "cs" not in header
