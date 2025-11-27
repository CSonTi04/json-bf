#!/usr/bin/env python3
"""
Cursed serializer: data ↔ Brainfuck program with optional gzip and HMAC.

Features:
- Encoder:  text → Brainfuck that prints that text
- Decoder:  Brainfuck → the text it prints
- JSON-based object encoding/decoding
- 3 encoding strategies:
    * stock            – simple per-character loopy encoder
    * cached           – reuse cells per repeating byte value
    * cached_heuristic – only cache frequent byte values
- HMAC-SHA256 header for tamper detection (optional via --no-mac)
- Verbose logging (--verbose)
- decode cache (LRU)
- decode-json / encode-json

Author: ChatGPT & András Tóth – Fuckupathon edition 😈
"""

from typing import Dict, List, Optional, Union
from collections import OrderedDict
import gzip
import json
import sys
import hmac
import hashlib

# -----------------------------------------
# Globals
# -----------------------------------------

BF_COMMANDS = set("+-<>[].,")
HEADER_COMMENT = "/// BFK1 JSON Brainfuck encoded\n"

# Demo secret key for HMAC; in real life, load from config/env
SECRET_KEY = b"super-secret-demo-key"

VERBOSE = False


def _log(msg: str):
    if VERBOSE:
        print(msg, file=sys.stderr)


# -----------------------------------------
# Header + HMAC utilities
# -----------------------------------------

def _split_header_and_body(full_text: str) -> tuple[str, str]:
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


def _compute_mac(body: str) -> str:
    return hmac.new(SECRET_KEY, body.encode("utf-8"), hashlib.sha256).hexdigest()


def _attach_mac_header(body: str) -> str:
    mac_hex = _compute_mac(body)
    header = HEADER_COMMENT + f"/// MAC hmac-sha256:{mac_hex}\n"
    return header + body


def _attach_header_no_mac(body: str) -> str:
    """
    Same as header, but no MAC line.
    """
    return HEADER_COMMENT + body


def _verify_mac_header(full_text: str) -> str:
    """
    Returns BF body. If MAC header exists -> verify it.
    If missing -> accept without verification.
    """
    header, body = _split_header_and_body(full_text)

    expected = None
    for line in header.splitlines():
        if "MAC hmac-sha256:" in line:
            expected = line.split("MAC hmac-sha256:", 1)[1].strip()

    if expected is None:
        _log("[security] no MAC found; skipping verification.")
        return body

    actual = _compute_mac(body)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("BFK1 MAC mismatch – tampered or corrupted data.")
    _log("[security] MAC verified OK.")
    return body


# -----------------------------------------
# LRU decode cache
# -----------------------------------------

_MAX_DECODE_CACHE = 64
_decode_cache: "OrderedDict[bytes, object]" = OrderedDict()


# -----------------------------------------
# Brainfuck Interpreter
# -----------------------------------------

def build_bracket_map(code: str) -> Dict[int, int]:
    stack = []
    bm = {}
    for i, c in enumerate(code):
        if c == "[":
            stack.append(i)
        elif c == "]":
            if not stack:
                raise SyntaxError(f"Unmatched ] at {i}")
            j = stack.pop()
            bm[i] = j
            bm[j] = i
    if stack:
        raise SyntaxError(f"Unmatched [ at {stack}")
    return bm


def brainfuck_interpret(
        code: str,
        input_data: str = "",
        max_steps: Optional[int] = None
) -> str:
    code = "".join(c for c in code if c in BF_COMMANDS)
    if not code:
        return ""

    bm = build_bracket_map(code)
    tape = [0] * 30000
    ptr = 0
    ip = 0
    out = []
    inp = 0
    steps = 0

    while ip < len(code):
        if max_steps is not None and steps >= max_steps:
            raise TimeoutError("Brainfuck exceeded max_steps")
        steps += 1

        c = code[ip]
        if c == ">":
            ptr += 1
            if ptr >= len(tape):
                tape.append(0)
        elif c == "<":
            if ptr == 0:
                raise RuntimeError("Pointer moved left of tape start")
            ptr -= 1
        elif c == "+":
            tape[ptr] = (tape[ptr] + 1) % 256
        elif c == "-":
            tape[ptr] = (tape[ptr] - 1) % 256
        elif c == ".":
            out.append(chr(tape[ptr]))
        elif c == ",":
            if inp < len(input_data):
                tape[ptr] = ord(input_data[inp]) % 256
                inp += 1
            else:
                tape[ptr] = 0
        elif c == "[":
            if tape[ptr] == 0:
                ip = bm[ip]
        elif c == "]":
            if tape[ptr] != 0:
                ip = bm[ip]

        ip += 1

    return "".join(out)


# -----------------------------------------
# Low-level BF building blocks
# -----------------------------------------

def _encode_char_loopy(val: int) -> str:
    q, r = divmod(val, 10)
    return (
            "[-]"
            ">[-]"
            + ("+" * q)
            + "[<++++++++++>-]"
            + "<"
            + ("+" * r)
            + "."
    )


def _build_value_loopy(val: int) -> str:
    q, r = divmod(val, 10)
    return (
            "[-]"
            ">[-]"
            + ("+" * q)
            + "[<++++++++++>-]"
            + "<"
            + ("+" * r)
    )


# -----------------------------------------
# Encoder strategies (return BF body only)
# -----------------------------------------

def encode_to_brainfuck_stock(text: str) -> str:
    return "".join(_encode_char_loopy(ord(ch)) for ch in text)


def encode_to_brainfuck_cached(text: str) -> str:
    parts = []
    cache: Dict[int, int] = {}
    cur = 0
    nxt = 0

    for ch in text:
        v = ord(ch)
        if v in cache:
            target = cache[v]
            delta = target - cur
            parts.append(">" * delta if delta > 0 else "<" * (-delta))
            parts.append(".")
            cur = target
            continue

        target = nxt
        delta = target - cur
        parts.append(">" * delta if delta > 0 else "<" * (-delta))
        cur = target

        parts.append(_build_value_loopy(v))
        parts.append(".")
        cache[v] = target
        nxt += 1

    return "".join(parts)


def encode_to_brainfuck_cached_heuristic(text: str, min_freq=3) -> str:
    freq = {}
    for ch in text:
        v = ord(ch)
        freq[v] = freq.get(v, 0) + 1

    parts = []
    cache: Dict[int, int] = {}
    cur = 0
    nxt = 0

    for ch in text:
        v = ord(ch)
        if v in cache:
            target = cache[v]
            delta = target - cur
            parts.append(">" * delta if delta > 0 else "<" * (-delta))
            parts.append(".")
            cur = target
            continue

        target = nxt
        delta = target - cur
        parts.append(">" * delta if delta > 0 else "<" * (-delta))
        cur = target

        parts.append(_build_value_loopy(v))
        parts.append(".")
        if freq.get(v, 0) >= min_freq:
            cache[v] = target
        nxt += 1

    return "".join(parts)


# -----------------------------------------
# Top-level BF encoder (with_header, use_hmac)
# -----------------------------------------

def encode_to_brainfuck(
        text: str,
        with_header: bool = True,
        strategy: str = "stock",
        use_hmac: bool = True,
) -> str:
    strategy = strategy.lower()
    _log(f"[encode] strategy={strategy}, len(text)={len(text)}, use_hmac={use_hmac}")

    if strategy == "stock":
        body = encode_to_brainfuck_stock(text)
    elif strategy == "cached":
        body = encode_to_brainfuck_cached(text)
    elif strategy in ("cached_heuristic", "cached-heuristic", "heuristic"):
        body = encode_to_brainfuck_cached_heuristic(text)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    if not with_header:
        return body

    if use_hmac:
        return _attach_mac_header(body)
    else:
        return _attach_header_no_mac(body)


# -----------------------------------------
# Gzip helpers
# -----------------------------------------

def is_gzip(data: bytes) -> bool:
    return len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B


def encode_to_gzip_bf(
        text: str,
        with_header: bool = True,
        strategy: str = "stock",
        use_hmac: bool = True,
) -> bytes:
    program = encode_to_brainfuck(
        text,
        with_header=with_header,
        strategy=strategy,
        use_hmac=use_hmac,
    )
    compressed = gzip.compress(program.encode("utf-8"))
    _log(
        f"[encode-gz] strategy={strategy}, bf_len={len(program)}, gz_len={len(compressed)}"
    )
    return compressed


# -----------------------------------------
# High-level JSON encode/decode
# -----------------------------------------

def encode_object(
        obj,
        compress: bool = True,
        strategy: str = "stock",
        use_hmac: bool = True,
):
    s = json.dumps(obj, ensure_ascii=True)
    _log(f"[encode_object] json_len={len(s)}, strategy={strategy}, use_hmac={use_hmac}")

    if compress:
        return encode_to_gzip_bf(
            s,
            with_header=True,
            strategy=strategy,
            use_hmac=use_hmac,
        )
    else:
        return encode_to_brainfuck(
            s,
            with_header=True,
            strategy=strategy,
            use_hmac=use_hmac,
        )


def _decode_from_bf_code(full_text: str):
    body = _verify_mac_header(full_text)
    _log(f"[decode] BF body len={len(body)}")
    out = brainfuck_interpret(body, max_steps=1_000_000)
    return json.loads(out)


def decode_object(data: Union[bytes, str]):
    if isinstance(data, bytes):
        key = data
    else:
        key = data.encode("utf-8", errors="replace")

    if key in _decode_cache:
        _log("[decode_object] cache HIT")
        _decode_cache.move_to_end(key)
        return _decode_cache[key]

    _log("[decode_object] cache MISS")

    if isinstance(data, bytes):
        if is_gzip(data):
            _log("[decode_object] decompressing gzip")
            full_text = gzip.decompress(data).decode("utf-8")
        else:
            full_text = data.decode("utf-8", errors="ignore")
    else:
        full_text = data

    obj = _decode_from_bf_code(full_text)
    _decode_cache[key] = obj
    if len(_decode_cache) > _MAX_DECODE_CACHE:
        _decode_cache.popitem(last=False)

    return obj


# -----------------------------------------
# CLI
# -----------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Cursed Brainfuck-based encoder/decoder with strategies, gzip, JSON, and optional HMAC."
    )
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="mode", required=True)

    # ---- encode (plain BF)
    enc = sub.add_parser("encode")
    enc.add_argument("text")
    enc.add_argument("--strategy", choices=["stock", "cached", "cached_heuristic"], default="stock")
    enc.add_argument("--no-header", action="store_true")
    enc.add_argument("--no-mac", action="store_true", help="Do not attach HMAC")

    # ---- encode-gz
    enc_gz = sub.add_parser("encode-gz")
    enc_gz.add_argument("text")
    enc_gz.add_argument("output")
    enc_gz.add_argument("--strategy", choices=["stock", "cached", "cached_heuristic"], default="stock")
    enc_gz.add_argument("--no-mac", action="store_true")

    # ---- encode-json
    enc_json = sub.add_parser("encode-json")
    enc_json.add_argument("json_file")
    enc_json.add_argument("--strategy", choices=["stock", "cached", "cached_heuristic"], default="stock")
    enc_json.add_argument("--no-mac", action="store_true")
    enc_json.add_argument("--no-compress", action="store_true")
    enc_json.add_argument("--output")

    # ---- decode-json
    dec_json = sub.add_parser("decode-json")
    dec_json.add_argument("file")
    dec_json.add_argument("--output")
    dec_json.add_argument("--pretty", action="store_true")

    # ---- decode (stdout)
    dec = sub.add_parser("decode")
    dec.add_argument("file")

    args = parser.parse_args()
    VERBOSE = args.verbose

    if args.mode == "encode":
        program = encode_to_brainfuck(
            args.text,
            with_header=not args.no_header,
            strategy=args.strategy,
            use_hmac=not args.no_mac,
        )
        print(program)

    elif args.mode == "encode-gz":
        program = encode_to_gzip_bf(
            args.text,
            with_header=True,
            strategy=args.strategy,
            use_hmac=not args.no_mac,
        )
        with open(args.output, "wb") as f:
            f.write(program)
        _log(f"[encode-gz] wrote {args.output}")

    elif args.mode == "encode-json":
        with open(args.json_file, "r", encoding="utf-8") as f:
            obj = json.load(f)

        if args.no_compress:
            data = encode_object(
                obj,
                compress=False,
                strategy=args.strategy,
                use_hmac=not args.no_mac,
            )
            out = args.output or (args.json_file + ".bf")
            with open(out, "w", encoding="utf-8") as f:
                f.write(data)
            _log(f"[encode-json] wrote {out}")
        else:
            data = encode_object(
                obj,
                compress=True,
                strategy=args.strategy,
                use_hmac=not args.no_mac,
            )
            out = args.output or (args.json_file + ".bf.gz")
            with open(out, "wb") as f:
                f.write(data)
            _log(f"[encode-json] wrote {out}")

    elif args.mode == "decode-json":
        with open(args.file, "rb") as f:
            raw = f.read()
        obj = decode_object(raw)

        out = args.output or (args.file + ".json")
        with open(out, "w", encoding="utf-8") as f:
            if args.pretty:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            else:
                json.dump(obj, f, ensure_ascii=False)
        _log(f"[decode-json] wrote {out}")

    elif args.mode == "decode":
        with open(args.file, "rb") as f:
            raw = f.read()
        obj = decode_object(raw)
        print(obj)
