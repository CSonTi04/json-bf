# test_cursed_format.py

import gzip
import json
import types

import pytest

import cursed_format as bfk


# ---------------------------
# Helpers
# ---------------------------

SIMPLE_OBJECTS = [
    {},
    {"msg": "Hello"},
    {"n": 42, "ok": True, "values": [1, 2, 3]},
    {"nested": {"a": 1, "b": [True, False, None]}},
    # ASCII-only JSON, but with unicode in source -> will be escaped
    {"msg": "Helló őűő"},
]

STRATEGIES = ["stock", "cached", "cached_heuristic"]


def split_header_and_body(full_text: str):
    """
    Local helper mirroring cursed_format._split_header_and_body,
    so we don't rely on internals.
    """
    lines = full_text.splitlines(keepends=True)
    header = []
    body = []
    in_header = True
    for line in lines:
        if in_header and line.startswith("///"):
            header.append(line)
        else:
            in_header = False
            body.append(line)
    return "".join(header), "".join(body)


# ---------------------------
# Round-trip tests
# ---------------------------

@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("compress", [False, True])
@pytest.mark.parametrize("use_hmac", [True, False])
@pytest.mark.parametrize("obj", SIMPLE_OBJECTS)
def test_roundtrip_encode_decode_object(strategy, compress, use_hmac, obj):
    """
    Basic sanity: any SIMPLE_OBJECTS round-trips through encode_object/decode_object
    for all strategies, compressed/uncompressed, with or without HMAC.
    """
    encoded = bfk.encode_object(
        obj,
        compress=compress,
        strategy=strategy,
        use_hmac=use_hmac,
    )

    # type of "encoded" depends on compress flag
    if compress:
        assert isinstance(encoded, (bytes, bytearray))
    else:
        assert isinstance(encoded, str)

    decoded = bfk.decode_object(encoded)
    assert decoded == obj


# ---------------------------
# Header / HMAC behavior
# ---------------------------

@pytest.mark.parametrize("strategy", STRATEGIES)
def test_header_contains_mac_when_use_hmac_true(strategy):
    """
    When use_hmac=True and with_header=True, the header should contain a MAC line.
    """
    text = '{"msg":"test"}'
    bf_text = bfk.encode_to_brainfuck(
        text,
        with_header=True,
        strategy=strategy,
        use_hmac=True,
    )
    header, body = split_header_and_body(bf_text)

    assert "/// BFK1 JSON Brainfuck encoded" in header
    assert "MAC hmac-sha256:" in header
    # body should be non-empty BF code
    assert body.strip() != ""


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_header_without_mac_when_use_hmac_false(strategy):
    """
    When use_hmac=False and with_header=True, we should get a header but no MAC line.
    """
    text = '{"msg":"test"}'
    bf_text = bfk.encode_to_brainfuck(
        text,
        with_header=True,
        strategy=strategy,
        use_hmac=False,
    )
    header, body = split_header_and_body(bf_text)

    assert "/// BFK1 JSON Brainfuck encoded" in header
    assert "MAC hmac-sha256:" not in header
    assert body.strip() != ""


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_no_header_when_with_header_false(strategy):
    """
    When with_header=False, we should get pure BF code (no leading '///').
    """
    text = '{"msg":"test"}'
    bf_text = bfk.encode_to_brainfuck(
        text,
        with_header=False,
        strategy=strategy,
        use_hmac=True,  # doesn't matter, header is disabled
    )
    # No header marker
    assert not bf_text.startswith("///")
    # Contains at least one BF command
    assert any(c in bfk.BF_COMMANDS for c in bf_text)


# ---------------------------
# HMAC tampering tests
# ---------------------------

@pytest.mark.parametrize("strategy", STRATEGIES)
def test_hmac_detects_tampering(strategy):
    """
    With use_hmac=True, modifying the BF body without updating the header MAC
    should cause decode_object to raise ValueError.
    """
    obj = {"msg": "tamper-test", "n": 123}
    encoded = bfk.encode_object(
        obj,
        compress=True,
        strategy=strategy,
        use_hmac=True,
    )
    assert isinstance(encoded, (bytes, bytearray))

    # Decompress to modify text
    assert bfk.is_gzip(encoded)
    text = gzip.decompress(encoded).decode("utf-8")

    header, body = split_header_and_body(text)
    # Flip something in the body (change last BF command if possible)
    if not body.strip():
        pytest.skip("Body unexpectedly empty; nothing to tamper with")

    # Find last BF command and change it to another valid command
    body_list = list(body)
    for i in range(len(body_list) - 1, -1, -1):
        if body_list[i] in bfk.BF_COMMANDS:
            # Replace '.' with '+' or '+' with '-', etc.
            if body_list[i] == ".":
                body_list[i] = "+"
            else:
                body_list[i] = "."
            break
    tampered_body = "".join(body_list)
    tampered_text = header + tampered_body
    tampered_encoded = gzip.compress(tampered_text.encode("utf-8"))

    # Now decoding should fail due to MAC mismatch
    with pytest.raises(ValueError):
        bfk.decode_object(tampered_encoded)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_no_hmac_allows_decode_after_body_change(strategy):
    """
    If use_hmac=False, there is no MAC line. Changing the body should NOT cause
    a MAC error (because there is no MAC to verify). It may of course produce
    invalid JSON, so we treat that as acceptable for this test.
    """
    obj = {"msg": "no-hmac-test", "n": 7}
    encoded = bfk.encode_object(
        obj,
        compress=True,
        strategy=strategy,
        use_hmac=False,
    )
    assert isinstance(encoded, (bytes, bytearray))

    assert bfk.is_gzip(encoded)
    text = gzip.decompress(encoded).decode("utf-8")
    header, body = split_header_and_body(text)

    # Tamper the body (same procedure as before)
    body_list = list(body)
    for i in range(len(body_list) - 1, -1, -1):
        if body_list[i] in bfk.BF_COMMANDS:
            body_list[i] = "." if body_list[i] != "." else "+"
            break
    tampered_body = "".join(body_list)
    tampered_text = header + tampered_body
    tampered_encoded = gzip.compress(tampered_text.encode("utf-8"))

    # decode_object should not raise MAC-related errors (no MAC present)
    try:
        _ = bfk.decode_object(tampered_encoded)
    except ValueError as e:
        # If we ever get a ValueError here, it should NOT be MAC-related
        # (it would much more likely be JSON decoding error, but we don't
        #  assert on that here).
        assert "MAC" not in str(e)


# ---------------------------
# Gzip + helpers sanity
# ---------------------------

def test_is_gzip_true_for_gzipped():
    data = b"hello"
    gz = gzip.compress(data)
    assert bfk.is_gzip(gz)


def test_is_gzip_false_for_plain():
    data = b"hello"
    assert not bfk.is_gzip(data)


# ---------------------------
# Decode cache sanity
# ---------------------------

def test_decode_cache_hit_and_miss():
    """
    Not deeply inspecting internal state, but we at least ensure that calling
    decode_object twice with the same bytes doesn't crash and uses cache path.
    """
    obj = {"msg": "cache-test", "n": 99}
    encoded = bfk.encode_object(obj, compress=True, strategy="stock", use_hmac=True)

    # First decode: MISS
    decoded1 = bfk.decode_object(encoded)
    # Second decode: HIT (internally)
    decoded2 = bfk.decode_object(encoded)

    assert decoded1 == decoded2 == obj
