# 🧠 BFK1 — The Cursed Brainfuck Serialization Format

*A deliberately absurd yet fully functional encoding for JSON using Brainfuck programs.*

![Brainfuck Banner](https://dummyimage.com/600x80/000/fff&text=BFK1+Serializer)

BFK1 takes JSON, turns it into a **Brainfuck program**, and optionally wraps it in **gzip**, optionally protecting it with **HMAC-SHA256**. Decoding is done by **running the Brainfuck code** to reconstruct the JSON.

Yes, seriously.  
Yes, it works.  
Yes, it’s cursed. 😈

---

# 📦 Features

- 🔥 **3 encoding strategies**
  - `stock` — naïve per-character Brainfuck
  - `cached` — Brainfuck value caching across cells
  - `cached_heuristic` — cache only frequently used bytes
- 🧊 **gzip** compression support (`.bf.gz`)
- 🔐 **Optional HMAC-SHA256 protection**
- 🧱 **Robust Brainfuck interpreter**
- ⚡ **LRU cache** for fast repeated decoding
- 🧩 **JSON ↔ Brainfuck ↔ JSON**
- 🛠️ Clean CLI
- 🧪 Fully tested (pytest)

---

# 🚀 Installation

```
git clone https://github.com/CSonTi04/json-bf
cd bfk1
```

Requires **Python ≥ 3.9**.

To run tests:

```
pip install pytest
pytest -q
```

---

# 🧬 Quick Start

## Encode text → Brainfuck

```
python3 cursed_format.py encode "Hello"
```

Output:

```
/// BFK1 JSON Brainfuck encoded
/// MAC hmac-sha256:92a4b3...
[-]>[-]+[<++++++++++>-]<+++++....
```

## Encode text → gzip
```
python3 cursed_format.py encode-gz "Hello World" out.bf.gz
```

## Encode JSON
```
python3 cursed_format.py encode-json data.json
```

Without gzip:
```
python3 cursed_format.py encode-json data.json --no-compress
```

Without HMAC:
```
python3 cursed_format.py encode-json data.json --no-mac
```

## Decode JSON
```
python3 cursed_format.py decode-json out.bf.gz
```

## Decode → Python object
```
python3 cursed_format.py decode out.bf.gz
```

---

# 🧠 How It Works

## 1. JSON → text
Serialized with `ensure_ascii=True`.

## 2. Text → Brainfuck
Each character becomes a BF routine that computes its byte value and prints it.

Example builder:
```
[-]>[-]+++[<++++++++++>-]<+++++.
```

## 3. gzip (optional)
BF compresses well due to repeated patterns.

## 4. HMAC (optional)
Header example:
```
/// MAC hmac-sha256:...
```

## 5. Decoding
We run the BF interpreter with safety guards and parse the output as JSON.

---

# 🧪 Python Examples

```
import cursed_format as bfk
obj = {"hello": "world", "n": 123}
enc = bfk.encode_object(obj, compress=True, strategy="cached")
dec = bfk.decode_object(enc)
print(dec)
```

Disable HMAC:
```
enc = bfk.encode_object({"msg": "no mac"}, compress=True, use_hmac=False)
print(bfk.decode_object(enc))
```

Tamper detection demo:
```
text = gzip.decompress(enc).decode("utf-8")
tampered = text.replace(".", "+", 1)
enc2 = gzip.compress(tampered.encode())
bfk.decode_object(enc2)  # raises ValueError
```

---

# 🔐 Strategy Comparison

| Strategy | Speed | Output Size | Notes |
|---------|-------|-------------|-------|
| stock | slow | big | naive |
| cached | fast | small | reuses cells |
| cached_heuristic | fastest | smallest | caches frequent bytes |

---

# 🧱 Format Layout

With HMAC:
```
/// BFK1 JSON Brainfuck encoded
/// MAC hmac-sha256:<hash>
<program>
```

Without HMAC:
```
/// BFK1 JSON Brainfuck encoded
<program>
```

---

# 🧯 Safety
- pointer boundary checks
- BF step limiter
- bracket matching
- HMAC tamper detection
- gzip header detection
- decode LRU cache

---

# 🧪 Tests

```
pip install pytest
pytest -q
```

---

# 🎉 Why BFK1?
Because normal formats are for cowards. This exists to confuse, amuse, and possibly horrify.
