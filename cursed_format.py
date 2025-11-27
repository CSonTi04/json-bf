#!/usr/bin/env python3
"""
Cursed serializer: data ↔ Brainfuck program with optional gzip.

Features:
- Encoder:  text → Brainfuck that prints that text
- Decoder:  Brainfuck → the text it prints
- JSON-based object encoding/decoding
- Magic header: '/// BFK1 JSON Brainfuck encoded'
- Smarter encoder variants (selectable):
    * stock            – simple per-character loopy encoder
    * cached           – cache byte values in dedicated tape cells
    * cached_heuristic – cache only frequently used bytes
- Optional gzip compression for the BF program
- Safety bits:
    * JSON uses ensure_ascii=True (ASCII-only JSON, no Unicode corruption)
    * Data pointer can't move left of tape start
    * brainfuck_interpret has a max_steps guard
- Decode caching:
    * decode_object caches last N decodes (LRU) keyed by input bytes/string
- HMAC-SHA256:
    * MAC over BF body stored in header
    * Verified before any Brainfuck is executed
- Verbose logging:
    * --verbose on CLI
    * Logs chosen strategy, sizes, cache hits, MAC status, etc.
"""

from typing import Dict, List, Optional, Union
from collections import OrderedDict
import gzip
import json
import sys
import hmac
import hashlib

BF_COMMANDS = set("+-<>[].,")
HEADER_COMMENT = "/// BFK1 JSON Brainfuck encoded\n"

# Demo secret key for HMAC; in real life, load this from env/config.
SECRET_KEY = b"super-secret-demo-key"

# Verbose logging flag (set from CLI)
VERBOSE = False  # set in main()


def _log(msg: str) -> None:
    if VERBOSE:
        print(msg, file=sys.stderr)


# -------------------------
# Header / HMAC helpers
# -------------------------

def _split_header_and_body(full_text: str) -> tuple[str, str]:
    """
    Split a BF source with optional header comments into (header, body).

    Header lines start with '///' and are kept separate from the rest.
    """
    lines = full_text.splitlines(keepends=True)
    header_lines: List[str] = []
    body_lines: List[str] = []

    in_header = True
    for line in lines:
        if in_header and line.startswith("///"):
            header_lines.append(line)
        else:
            in_header = False
            body_lines.append(line)

    return "".join(header_lines), "".join(body_lines)


def _compute_mac(body: str) -> str:
    """
    Compute HMAC-SHA256 over the BF body using SECRET_KEY.
    """
    return hmac.new(SECRET_KEY, body.encode("utf-8"), hashlib.sha256).hexdigest()


def _attach_mac_header(body: str) -> str:
    """
    Build full text = header + MAC line + body.
    """
    mac_hex = _compute_mac(body)
    header = HEADER_COMMENT + f"/// MAC hmac-sha256:{mac_hex}\n"
    return header + body


def _verify_mac_header(full_text: str) -> str:
    """
    Verify HMAC-SHA256 in header (if present), return BF body.

    - If MAC line present and mismatch -> raise ValueError.
    - If MAC line missing -> log a warning (if verbose) and trust body.
    """
    header, body = _split_header_and_body(full_text)

    expected = None
    for line in header.splitlines():
        line = line.strip()
        if line.startswith("///") and "MAC hmac-sha256:" in line:
            expected = line.split("MAC hmac-sha256:", 1)[1].strip()

    if expected is None:
        _log("[security] no MAC header found; accepting body without verification")
        return body

    actual = _compute_mac(body)
    if not hmac.compare_digest(actual, expected):
        raise ValueError("BFK1 MAC mismatch – data may be corrupted or tampered.")

    _log("[security] MAC verified successfully")
    return body


# -------------------------
# Decode cache (object-level)
# -------------------------

_MAX_DECODE_CACHE = 64
_decode_cache: "OrderedDict[bytes, object]" = OrderedDict()


# -------------------------
# Brainfuck interpreter
# -------------------------

def build_bracket_map(code: str) -> Dict[int, int]:
    stack: List[int] = []
    bracket_map: Dict[int, int] = {}

    for i, c in enumerate(code):
        if c == "[":
            stack.append(i)
        elif c == "]":
            if not stack:
                raise SyntaxError(f"Unmatched ']' at position {i}")
            j = stack.pop()
            bracket_map[i] = j
            bracket_map[j] = i

    if stack:
        raise SyntaxError(f"Unmatched '[' at positions {stack}")

    return bracket_map


def brainfuck_interpret(
    code: str,
    input_data: str = "",
    max_steps: Optional[int] = None,
) -> str:
    """
    Execute Brainfuck code and return its output as a string.

    input_data: optional stdin for ',' commands.
    max_steps: if not None, raise TimeoutError after this many instructions.
    """
    # Strip everything that is not a BF command (drops header/comments too)
    code = "".join(c for c in code if c in BF_COMMANDS)

    if not code:
        return ""

    bracket_map = build_bracket_map(code)

    tape = [0] * 30000
    ptr = 0           # data pointer
    ip = 0            # instruction pointer
    out: List[str] = []
    input_pos = 0
    steps = 0

    while ip < len(code):
        if max_steps is not None and steps >= max_steps:
            raise TimeoutError("Brainfuck program exceeded max_steps")
        steps += 1

        cmd = code[ip]

        if cmd == ">":
            ptr += 1
            if ptr >= len(tape):
                tape.append(0)
        elif cmd == "<":
            if ptr == 0:
                raise RuntimeError("Data pointer moved left of tape start")
            ptr -= 1
        elif cmd == "+":
            tape[ptr] = (tape[ptr] + 1) % 256
        elif cmd == "-":
            tape[ptr] = (tape[ptr] - 1) % 256
        elif cmd == ".":
            out.append(chr(tape[ptr]))
        elif cmd == ",":
            if input_pos < len(input_data):
                tape[ptr] = ord(input_data[input_pos]) % 256
                input_pos += 1
            else:
                tape[ptr] = 0
        elif cmd == "[":
            if tape[ptr] == 0:
                ip = bracket_map[ip]
        elif cmd == "]":
            if tape[ptr] != 0:
                ip = bracket_map[ip]

        ip += 1

    return "".join(out)


# -------------------------
# Low-level per-byte builders
# -------------------------

def _encode_char_loopy(val: int) -> str:
    """
    Encode a single byte value as Brainfuck using a base-10 loop
    and immediately print it.
    """
    q, r = divmod(val, 10)
    parts: List[str] = []

    parts.append("[-]")
    parts.append(">[-]")
    parts.append("+" * q)
    parts.append("[<++++++++++>-]")
    parts.append("<")
    parts.append("+" * r)
    parts.append(".")

    return "".join(parts)


def _build_value_loopy(val: int) -> str:
    """
    Like _encode_char_loopy, but only builds the value in the current cell
    without printing. Pointer starts and ends on the same cell.
    """
    q, r = divmod(val, 10)
    parts: List[str] = []

    parts.append("[-]")
    parts.append(">[-]")
    parts.append("+" * q)
    parts.append("[<++++++++++>-]")
    parts.append("<")
    parts.append("+" * r)

    return "".join(parts)


# -------------------------
# Encoder strategies
# -------------------------

def encode_to_brainfuck_stock(text: str, with_header: bool = True) -> str:
    """
    STOCK encoder:
      - For each character, build it from scratch with the loopy pattern.
      - Doesn't reuse any cells.
    Returns BF body (no header).
    """
    parts: List[str] = []
    for ch in text:
        parts.append(_encode_char_loopy(ord(ch)))
    program = "".join(parts)
    return program  # header added later


def encode_to_brainfuck_cached(text: str, with_header: bool = True) -> str:
    """
    CACHED encoder:
      - Maintains a value -> cell index cache.
      - First time we see a byte value, we build it in a fresh cell.
      - Subsequent uses:
          * Move pointer to that cell
          * Print '.'
    Returns BF body (no header).
    """
    parts: List[str] = []

    cache: Dict[int, int] = {}
    cur_cell = 0
    next_free_cell = 0

    for ch in text:
        val = ord(ch)

        if val in cache:
            target = cache[val]
            move = target - cur_cell
            if move > 0:
                parts.append(">" * move)
            elif move < 0:
                parts.append("<" * (-move))
            parts.append(".")
            cur_cell = target
            continue

        target = next_free_cell
        move = target - cur_cell
        if move > 0:
            parts.append(">" * move)
        elif move < 0:
            parts.append("<" * (-move))
        cur_cell = target

        parts.append(_build_value_loopy(val))
        parts.append(".")

        cache[val] = target
        next_free_cell += 1

    program = "".join(parts)
    return program  # header added later


def encode_to_brainfuck_cached_heuristic(
    text: str,
    with_header: bool = True,
    min_freq: int = 3,
) -> str:
    """
    CACHED_HEURISTIC encoder:
      - First pass: count frequency of each byte.
      - Second pass:
          * If a value appears >= min_freq times:
              - Assign a dedicated cache cell (value -> cell index)
              - Reuse it for every occurrence
          * If a value appears less often:
              - Build it in a new cell but do NOT store in the cache.
    Returns BF body (no header).
    """
    freq: Dict[int, int] = {}
    for ch in text:
        v = ord(ch)
        freq[v] = freq.get(v, 0) + 1

    parts: List[str] = []
    cache: Dict[int, int] = {}
    cur_cell = 0
    next_free_cell = 0

    for ch in text:
        val = ord(ch)

        if val in cache:
            target = cache[val]
            move = target - cur_cell
            if move > 0:
                parts.append(">" * move)
            elif move < 0:
                parts.append("<" * (-move))
            parts.append(".")
            cur_cell = target
            continue

        target = next_free_cell
        move = target - cur_cell
        if move > 0:
            parts.append(">" * move)
        elif move < 0:
            parts.append("<" * (-move))
        cur_cell = target

        parts.append(_build_value_loopy(val))
        parts.append(".")

        if freq.get(val, 0) >= min_freq:
            cache[val] = target

        next_free_cell += 1

    program = "".join(parts)
    return program  # header added later


def encode_to_brainfuck(
    text: str,
    with_header: bool = True,
    strategy: str = "stock",
) -> str:
    """
    Dispatch to the chosen encoder strategy.

    strategy:
      - "stock"
      - "cached"
      - "cached_heuristic" / "cached-heuristic" / "heuristic"
    """
    strategy_norm = strategy.lower()
    _log(f"[encode] strategy={strategy_norm}, len(text)={len(text)}")

    if strategy_norm == "stock":
        body = encode_to_brainfuck_stock(text, with_header=False)
    elif strategy_norm == "cached":
        body = encode_to_brainfuck_cached(text, with_header=False)
    elif strategy_norm in ("cached_heuristic", "cached-heuristic", "heuristic"):
        body = encode_to_brainfuck_cached_heuristic(text, with_header=False)
    else:
        raise ValueError(f"Unknown encoding strategy: {strategy}")

    if with_header:
        return _attach_mac_header(body)
    else:
        return body


# -------------------------
# Gzip helpers
# -------------------------

def is_gzip(data: bytes) -> bool:
    """
    Simple magic-number check for gzip:
    First two bytes should be 0x1f, 0x8b.
    """
    return len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B


def encode_to_gzip_bf(
    text: str,
    with_header: bool = True,
    strategy: str = "stock",
) -> bytes:
    """
    Encode text to Brainfuck using the selected strategy, then gzip-compress it.
    """
    program = encode_to_brainfuck(text, with_header=with_header, strategy=strategy)
    compressed = gzip.compress(program.encode("utf-8"))
    _log(
        f"[encode-gz] strategy={strategy.lower()}, "
        f"bf_len={len(program)}, gz_len={len(compressed)}"
    )
    return compressed


# -------------------------
# “Format” helpers: objects
# -------------------------

def encode_object(obj, compress: bool = True, strategy: str = "stock"):
    """
    High-level encoder: Python object -> JSON -> Brainfuck.

    - JSON is produced with ensure_ascii=True, so it's ASCII-only.
    - If compress=True (default), returns gzip-compressed bytes.
    - If compress=False, returns the raw BF program as a string.
    """
    s = json.dumps(obj, ensure_ascii=True)
    _log(
        f"[encode_object] strategy={strategy.lower()}, json_len={len(s)}, compress={compress}"
    )

    if compress:
        return encode_to_gzip_bf(s, with_header=True, strategy=strategy)
    else:
        return encode_to_brainfuck(s, with_header=True, strategy=strategy)


def _decode_from_bf_code(full_text: str):
    """
    full_text: BF source including optional header and MAC line.
    """
    # verify MAC (if present) and get pure BF body
    body = _verify_mac_header(full_text)
    _log(f"[decode] running brainfuck interpreter, bf_len={len(body)}")
    out = brainfuck_interpret(body, max_steps=1_000_000)
    return json.loads(out)


def decode_object(data: Union[bytes, str]):
    """
    High-level decoder with caching.

    - Accepts bytes or string.
    - If bytes:
        * If gzip magic: decompress, then interpret as UTF-8 Brainfuck+header.
        * Else: treat bytes as UTF-8 Brainfuck+header directly.
    - If string:
        * Treat as raw Brainfuck+header source.

    Caching:
    - Uses an LRU-style cache keyed by the original input (bytes or
      string converted to bytes) to avoid repeated decoding work.
    """
    # Normalize key for cache (always bytes)
    if isinstance(data, bytes):
        key = data
        if key in _decode_cache:
            _log("[decode_object] cache HIT (bytes)")
            _decode_cache.move_to_end(key)
            return _decode_cache[key]

        _log("[decode_object] cache MISS (bytes)")

        if is_gzip(key):
            _log("[decode_object] detected gzip; decompressing")
            full_text = gzip.decompress(key).decode("utf-8")
        else:
            full_text = key.decode("utf-8", errors="ignore")

    else:
        key = data.encode("utf-8", errors="replace")
        if key in _decode_cache:
            _log("[decode_object] cache HIT (str)")
            _decode_cache.move_to_end(key)
            return _decode_cache[key]

        _log("[decode_object] cache MISS (str)")
        full_text = data

    obj = _decode_from_bf_code(full_text)

    # Store in LRU cache
    _decode_cache[key] = obj
    if len(_decode_cache) > _MAX_DECODE_CACHE:
        _decode_cache.popitem(last=False)

    return obj


# -------------------------
# Simple CLI usage
# -------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Cursed Brainfuck-based encoder/decoder (with optional gzip, strategies, and HMAC)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="enable verbose logging to stderr",
    )

    sub = parser.add_subparsers(dest="mode", required=True)

    # encode → plain BF to stdout (for demo / readability)
    enc = sub.add_parser("encode", help="encode text to Brainfuck (plain text)")
    enc.add_argument("text", help="text to encode")
    enc.add_argument(
        "--no-header",
        action="store_true",
        help="omit the magic header + MAC line",
    )
    enc.add_argument(
        "--strategy",
        choices=["stock", "cached", "cached_heuristic"],
        default="stock",
        help="encoder strategy to use",
    )

    # encode-gz → gzipped BF to file (the 'real' format)
    enc_gz = sub.add_parser("encode-gz", help="encode text to gzipped Brainfuck file")
    enc_gz.add_argument("text", help="text to encode")
    enc_gz.add_argument("output", help="output .bf.gz file path")
    enc_gz.add_argument(
        "--strategy",
        choices=["stock", "cached", "cached_heuristic"],
        default="stock",
        help="encoder strategy to use",
    )

    # encode-json → read JSON file, encode via encode_object, output .bf or .bf.gz
    enc_json = sub.add_parser(
        "encode-json",
        help="encode a JSON file to Brainfuck format (.bf or .bf.gz)",
    )
    enc_json.add_argument("json_file", help="path to input .json file")
    enc_json.add_argument(
        "--strategy",
        choices=["stock", "cached", "cached_heuristic"],
        default="stock",
        help="encoder strategy to use",
    )
    enc_json.add_argument(
        "--no-compress",
        action="store_true",
        help="output plain .bf (no gzip), default = .bf.gz",
    )
    enc_json.add_argument(
        "--output",
        help="path for output file; default is json_file + .bf or .bf.gz",
    )

    # decode-json → BF / BF.gz → JSON file
    dec_json = sub.add_parser(
        "decode-json",
        help="decode a Brainfuck-based file (.bf or .bf.gz) back to JSON file",
    )
    dec_json.add_argument("file", help="input .bf or .bf.gz file")
    dec_json.add_argument(
        "--output",
        help="path for output .json file; default is input + '.json'",
    )
    dec_json.add_argument(
        "--pretty",
        action="store_true",
        help="pretty-print JSON with indentation",
    )

    # decode → use decode_object, print Python object
    dec = sub.add_parser(
        "decode",
        help="decode Brainfuck (plain or .gz) to Python object (via JSON)",
    )
    dec.add_argument("file", help="Brainfuck source file (.bf or .bf.gz)")

    args = parser.parse_args()

    # set global verbose flag
    VERBOSE = args.verbose
    if VERBOSE:
        _log(f"[main] mode={args.mode}")

    if args.mode == "encode":
        program = encode_to_brainfuck(
            args.text,
            with_header=not args.no_header,
            strategy=args.strategy,
        )
        print(program)

    elif args.mode == "encode-gz":
        program_gz = encode_to_gzip_bf(
            args.text,
            with_header=True,
            strategy=args.strategy,
        )
        with open(args.output, "wb") as f:
            f.write(program_gz)
        _log(f"[encode-gz] wrote {args.output}")

    elif args.mode == "encode-json":
        # Load JSON from file
        with open(args.json_file, "r", encoding="utf-8") as f:
            obj = json.load(f)
        _log(f"[encode-json] loaded {args.json_file}")

        if args.no_compress:
            data_str = encode_object(obj, compress=False, strategy=args.strategy)
            out_path = args.output or (args.json_file + ".bf")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(data_str)
            _log(f"[encode-json] wrote plain BF to {out_path}")
        else:
            data_bytes = encode_object(obj, compress=True, strategy=args.strategy)
            out_path = args.output or (args.json_file + ".bf.gz")
            with open(out_path, "wb") as f:
                f.write(data_bytes)
            _log(f"[encode-json] wrote gzipped BF to {out_path}")

    elif args.mode == "decode-json":
        # Read BF/BF.gz as bytes, let decode_object handle everything
        with open(args.file, "rb") as f:
            raw = f.read()
        obj = decode_object(raw)

        out_path = args.output or (args.file + ".json")
        _log(f"[decode-json] writing JSON to {out_path}")

        with open(out_path, "w", encoding="utf-8") as f:
            if args.pretty:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            else:
                json.dump(obj, f, ensure_ascii=False)

        _log("[decode-json] done")

    elif args.mode == "decode":
        with open(args.file, "rb") as f:
            raw = f.read()
        obj = decode_object(raw)
        print(obj)
