"""Regression checks for the dependency fixes in Issue #164 (offline)."""
from datetime import datetime, timedelta, timezone
from http.client import HTTPResponse as StdlibResponse
from io import BytesIO
from pathlib import Path
import tomllib

import jwt
import pytest
from jwt.exceptions import ExpiredSignatureError, ImmatureSignatureError, InvalidSignatureError
from urllib3.exceptions import ProtocolError
from urllib3.response import HTTPResponse

ROOT = Path(__file__).resolve().parents[1]
KEY = "dependency-regression-test-key-not-a-production-secret-64-characters"


@pytest.mark.parametrize("name,floor", [("pyjwt", (2, 15, 1)), ("urllib3", (2, 8, 0))])
def test_security_floor_in_lock_and_constraints(name, floor):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    package = next(p for p in lock["package"] if p["name"] == name)
    assert floor <= tuple(int(n) for n in package["version"].split(".")) < (3,)
    requirement = f"{'PyJWT' if name == 'pyjwt' else name}>={'.'.join(map(str, floor))},<3"
    assert requirement in project["tool"]["uv"]["constraint-dependencies"]


def test_jwt_valid_token_still_decodes():
    token = jwt.encode({"sub": "test-user", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, KEY, algorithm="HS256")
    assert jwt.decode(token, KEY, algorithms=["HS256"])["sub"] == "test-user"


@pytest.mark.parametrize("claim,error,offset", [
    ("exp", ExpiredSignatureError, -3600),
    ("nbf", ImmatureSignatureError, 3600),
])
def test_reused_options_do_not_disable_claim_validation(claim, error, offset):
    # CVE-2026-103001: unsigned inspection must not mutate the caller's options.
    now = datetime.now(timezone.utc)
    token = jwt.encode({claim: int(now.timestamp()) + offset}, KEY, algorithm="HS256")
    options = {"verify_signature": False}
    jwt.decode(token, algorithms=["HS256"], options=options)
    assert options == {"verify_signature": False}
    options["verify_signature"] = True
    with pytest.raises(error):
        jwt.decode(token, KEY, algorithms=["HS256"], options=options)
    assert options == {"verify_signature": True}


def test_jwt_tampered_signature_remains_rejected():
    token = jwt.encode({"sub": "test-user"}, KEY, algorithm="HS256")
    with pytest.raises(InvalidSignatureError):
        jwt.decode(token, "different-test-key-that-is-also-long-enough-for-hmac-validation", algorithms=["HS256"])


class ResponseSocket:
    def __init__(self, chunks):
        self.stream = BytesIO(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n" + chunks)

    def makefile(self, *args, **kwargs):
        return self.stream


def chunked_response(chunks):
    response = StdlibResponse(ResponseSocket(chunks))
    response.begin()
    return HTTPResponse(body=response, headers=dict(response.headers.items()), preload_content=False)


def test_urllib3_regular_chunked_body_still_reads():
    response = chunked_response(b"5\r\nhello\r\n0\r\n\r\n")
    assert b"".join(response.read_chunked()) == b"hello"


def test_urllib3_rejects_unbounded_chunk_size_line():
    # GHSA-vxq7-64xx-v4gw: chunk extensions must not allow unbounded buffering.
    response = chunked_response(b"1;" + b"a" * 65536 + b"\r\nx\r\n0\r\n\r\n")
    with pytest.raises(ProtocolError, match="chunk size line exceeded"):
        list(response.read_chunked())
    assert response.closed
