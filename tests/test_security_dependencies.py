"""Offline regression checks for dependency security floors (Issues #164/#220)."""
from datetime import datetime, timedelta, timezone
from http.client import HTTPResponse as StdlibResponse
from io import BytesIO
from pathlib import Path
import tomllib
import sys

import pytest
from urllib3.exceptions import ProtocolError
from urllib3.response import HTTPResponse

ROOT = Path(__file__).resolve().parents[1]
KEY = "dependency-regression-test-key-not-a-production-secret-64-characters"


@pytest.mark.parametrize("name,floor,upper", [
    ("pyjwt", (2, 15, 1), 3),
    ("urllib3", (2, 8, 0), 3),
    ("multidict", (6, 9, 1), 7),
])
def test_security_floor_in_lock_and_constraints(name, floor, upper):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    package = next(p for p in lock["package"] if p["name"] == name)
    assert floor <= tuple(int(n) for n in package["version"].split(".")) < (upper,)
    specifier = f">={'.'.join(map(str, floor))},<{upper}"
    requirement = f"{'PyJWT' if name == 'pyjwt' else name}{specifier}"
    assert requirement in project["tool"]["uv"]["constraint-dependencies"]
    assert {"name": name, "specifier": specifier} in lock["manifest"]["constraints"]


@pytest.mark.parametrize("dictionary_name", ["MultiDict", "CIMultiDict"])
@pytest.mark.parametrize("operation", ["reflected_union", "subtraction"])
def test_multidict_items_operations_release_operand_references(dictionary_name, operation):
    # GHSA-54p9-h82j-f925 / CVE-2026-104874: keep the probe small and offline.
    # CPython reference counts verify release, without memory/RSS heuristics.
    if sys.implementation.name != "cpython":
        pytest.skip("Reference counts are specific to CPython")
    # multidict belongs to optional extras, not the base/dev environment.
    multidict = pytest.importorskip("multidict")
    dictionary = getattr(multidict, dictionary_name)
    data = dictionary({"seed": "initial"})
    value = object()
    operand = [(f"key-{index}", value) for index in range(32)]
    before = sys.getrefcount(value)
    result = operand | data.items() if operation == "reflected_union" else data.items() - operand
    assert result
    del result
    assert sys.getrefcount(value) == before


@pytest.fixture
def jwt_library():
    # JWT remains in the optional OpenBB extra after MCP removal, not base/dev.
    return pytest.importorskip("jwt")


def test_jwt_valid_token_still_decodes(jwt_library):
    jwt = jwt_library
    token = jwt.encode({"sub": "test-user", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, KEY, algorithm="HS256")
    assert jwt.decode(token, KEY, algorithms=["HS256"])["sub"] == "test-user"


@pytest.mark.parametrize("claim,error,offset", [
    ("exp", "ExpiredSignatureError", -3600),
    ("nbf", "ImmatureSignatureError", 3600),
])
def test_reused_options_do_not_disable_claim_validation(claim, error, offset, jwt_library):
    jwt = jwt_library
    error = getattr(jwt.exceptions, error)
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


def test_jwt_tampered_signature_remains_rejected(jwt_library):
    jwt = jwt_library
    token = jwt.encode({"sub": "test-user"}, KEY, algorithm="HS256")
    with pytest.raises(jwt.exceptions.InvalidSignatureError):
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
