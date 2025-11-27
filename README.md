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

```bash
git clone https://github.com/CSonTi04/json-bf
cd json-bf
```

Requires **Python ≥ 3.9**.

To run tests:

```bash
pip install pytest
pytest -q
```

---

# 🧬 Quick Start

## Encode text → Brainfuck

```bash
python cursed_format.py encode "Hello"
```

Output:

```
/// BFK1 JSON Brainfuck encoded
/// MAC hmac-sha256:92a4b3...
[-]>[-]+[<++++++++++>-]<+++++....
```

## Encode text → gzip
```bash
python cursed_format.py encode-gz "Hello World" out.bf.gz
```

---

# 📂 Test Files Quick Reference

## Format Comparison

| Format       | Extension | Compression | Command Flag    | File Size |
|--------------|-----------|-------------|-----------------|-----------|
| Compressed   | `.bf.gz`  | Yes (gzip)  | *(default)*     | Smallest  |
| Uncompressed | `.bf`     | No          | `--no-compress` | Larger    |

## Workflow Overview

**Compressed workflow (default):**
```bash
# Encode: JSON → .bf.gz
python cursed_format.py encode-json .\test_data\64KB.json
# Decode: .bf.gz → JSON
python cursed_format.py decode-json .\test_data\64KB.json.bf.gz
```

**Uncompressed workflow:**
```bash
# Encode: JSON → .bf (plain text Brainfuck)
python cursed_format.py encode-json .\test_data\64KB.json --no-compress
# Decode: .bf → JSON
python cursed_format.py decode-json .\test_data\64KB.json.bf
```

---

# 📂 Encoding Test Files (Compressed)

## Encode 64KB JSON
```bash
python cursed_format.py encode-json .\test_data\64KB.json
# Creates: .\test_data\64KB.json.bf.gz
```

## Encode 128KB JSON
```bash
python cursed_format.py encode-json .\test_data\128KB.json
# Creates: .\test_data\128KB.json.bf.gz
```

## Encode 256KB JSON
```bash
python cursed_format.py encode-json .\test_data\256KB.json
# Creates: .\test_data\256KB.json.bf.gz
```

## Encode 512KB JSON
```bash
python cursed_format.py encode-json .\test_data\512KB.json
# Creates: .\test_data\512KB.json.bf.gz
```

## Encode 1MB JSON
```bash
python cursed_format.py encode-json .\test_data\1MB.json
# Creates: .\test_data\1MB.json.bf.gz
```

## Encode 5MB JSON
```bash
python cursed_format.py encode-json .\test_data\5MB.json
# Creates: .\test_data\5MB.json.bf.gz
```

---

# 📂 Encoding Test Files (Uncompressed)

## Encode 64KB JSON (no compression)
```bash
python cursed_format.py encode-json .\test_data\64KB.json --no-compress
# Creates: .\test_data\64KB.json.bf
```

## Encode 128KB JSON (no compression)
```bash
python cursed_format.py encode-json .\test_data\128KB.json --no-compress
# Creates: .\test_data\128KB.json.bf
```

## Encode 256KB JSON (no compression)
```bash
python cursed_format.py encode-json .\test_data\256KB.json --no-compress
# Creates: .\test_data\256KB.json.bf
```

## Encode 512KB JSON (no compression)
```bash
python cursed_format.py encode-json .\test_data\512KB.json --no-compress
# Creates: .\test_data\512KB.json.bf
```

## Encode 1MB JSON (no compression)
```bash
python cursed_format.py encode-json .\test_data\1MB.json --no-compress
# Creates: .\test_data\1MB.json.bf
```

## Encode 5MB JSON (no compression)
```bash
python cursed_format.py encode-json .\test_data\5MB.json --no-compress
# Creates: .\test_data\5MB.json.bf
```

---

# 📂 Decoding Compressed Files (.bf.gz)

## Decode 64KB → JSON
```bash
python cursed_format.py decode-json .\test_data\64KB.json.bf.gz
# Creates: .\test_data\64KB.json.bf.gz.json
```

## Decode 128KB → JSON
```bash
python cursed_format.py decode-json .\test_data\128KB.json.bf.gz
# Creates: .\test_data\128KB.json.bf.gz.json
```

## Decode 256KB → JSON
```bash
python cursed_format.py decode-json .\test_data\256KB.json.bf.gz
# Creates: .\test_data\256KB.json.bf.gz.json
```

## Decode 512KB → JSON
```bash
python cursed_format.py decode-json .\test_data\512KB.json.bf.gz
# Creates: .\test_data\512KB.json.bf.gz.json
```

## Decode 1MB → JSON
```bash
python cursed_format.py decode-json .\test_data\1MB.json.bf.gz
# Creates: .\test_data\1MB.json.bf.gz.json
```

## Decode 5MB → JSON
```bash
python cursed_format.py decode-json .\test_data\5MB.json.bf.gz
# Creates: .\test_data\5MB.json.bf.gz.json
```

---

# 📂 Decoding Uncompressed Files (.bf)

## Decode 64KB → JSON
```bash
python cursed_format.py decode-json .\test_data\64KB.json.bf
# Creates: .\test_data\64KB.json.bf.json
```

## Decode 128KB → JSON
```bash
python cursed_format.py decode-json .\test_data\128KB.json.bf
# Creates: .\test_data\128KB.json.bf.json
```

## Decode 256KB → JSON
```bash
python cursed_format.py decode-json .\test_data\256KB.json.bf
# Creates: .\test_data\256KB.json.bf.json
```

## Decode 512KB → JSON
```bash
python cursed_format.py decode-json .\test_data\512KB.json.bf
# Creates: .\test_data\512KB.json.bf.json
```

## Decode 1MB → JSON
```bash
python cursed_format.py decode-json .\test_data\1MB.json.bf
# Creates: .\test_data\1MB.json.bf.json
```

## Decode 5MB → JSON
```bash
python cursed_format.py decode-json .\test_data\5MB.json.bf
# Creates: .\test_data\5MB.json.bf.json
```

---

# 📦 Direct Gzip Compression (No Brainfuck)

For comparison, you can compress JSON files directly with gzip without Brainfuck encoding:

## Compress 64KB JSON
```bash
python -c "import gzip, shutil; shutil.copyfileobj(open(r'.\test_data\64KB.json', 'rb'), gzip.open(r'.\test_data\64KB.json.gz', 'wb'))"
```

## Compress 128KB JSON
```bash
python -c "import gzip, shutil; shutil.copyfileobj(open(r'.\test_data\128KB.json', 'rb'), gzip.open(r'.\test_data\128KB.json.gz', 'wb'))"
```

## Compress 256KB JSON
```bash
python -c "import gzip, shutil; shutil.copyfileobj(open(r'.\test_data\256KB.json', 'rb'), gzip.open(r'.\test_data\256KB.json.gz', 'wb'))"
```

## Compress 512KB JSON
```bash
python -c "import gzip, shutil; shutil.copyfileobj(open(r'.\test_data\512KB.json', 'rb'), gzip.open(r'.\test_data\512KB.json.gz', 'wb'))"
```

## Compress 1MB JSON
```bash
python -c "import gzip, shutil; shutil.copyfileobj(open(r'.\test_data\1MB.json', 'rb'), gzip.open(r'.\test_data\1MB.json.gz', 'wb'))"
```

## Compress 5MB JSON
```bash
python -c "import gzip, shutil; shutil.copyfileobj(open(r'.\test_data\5MB.json', 'rb'), gzip.open(r'.\test_data\5MB.json.gz', 'wb'))"
```

## Decompress all gzipped files
```bash
python -c "import gzip, shutil, glob; [shutil.copyfileobj(gzip.open(f, 'rb'), open(f[:-3] + '.decompressed.json', 'wb')) for f in glob.glob(r'.\test_data\*.json.gz')]"
```

---

# 🎯 Advanced Options

## Encode with custom output file
```bash
python cursed_format.py encode-json .\test_data\64KB.json --output custom.bf.gz
```

## Encode without compression (plain text Brainfuck)
```bash
python cursed_format.py encode-json .\test_data\64KB.json --no-compress
# Creates: .\test_data\64KB.json.bf (uncompressed text)
```

## Encode without HMAC protection
```bash
python cursed_format.py encode-json .\test_data\64KB.json --no-mac
```

## Encode with different strategies
```bash
# Stock strategy (naive)
python cursed_format.py encode-json .\test_data\64KB.json --strategy stock

# Cached strategy (reuses cells)
python cursed_format.py encode-json .\test_data\64KB.json --strategy cached

# Cached heuristic (fastest, smallest)
python cursed_format.py encode-json .\test_data\64KB.json --strategy cached_heuristic
```

## Decode with pretty printing
```bash
python cursed_format.py decode-json .\test_data\64KB.json.bf.gz --pretty
```

## Decode with custom output file
```bash
python cursed_format.py decode-json .\test_data\64KB.json.bf.gz --output decoded.json
```

## Decode to stdout (print as Python object)
```bash
python cursed_format.py decode .\test_data\64KB.json.bf.gz
```

## Verbose mode (see what's happening)
```bash
python cursed_format.py --verbose encode-json .\test_data\64KB.json
python cursed_format.py --verbose decode-json .\test_data\64KB.json.bf.gz
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

# 🧪 Python API Examples

## Basic usage
```python
import cursed_format as bfk

# Encode a Python object
obj = {"hello": "world", "n": 123}
enc = bfk.encode_object(obj, compress=True, strategy="cached")

# Decode it back
dec = bfk.decode_object(enc)
print(dec)  # {"hello": "world", "n": 123}
```

## Disable HMAC
```python
import cursed_format as bfk

enc = bfk.encode_object({"msg": "no mac"}, compress=True, use_hmac=False)
print(bfk.decode_object(enc))
```

## Encode from test files
```python
import json
import cursed_format as bfk

# Load and encode test file
with open("test_data/64KB.json", "r") as f:
    data = json.load(f)

# Encode with cached_heuristic strategy
encoded = bfk.encode_object(data, compress=True, strategy="cached_heuristic")

# Save to file
with open("test_data/64KB.json.bf.gz", "wb") as f:
    f.write(encoded)

# Decode back
with open("test_data/64KB.json.bf.gz", "rb") as f:
    decoded = bfk.decode_object(f.read())

print(decoded == data)  # True
```

## Tamper detection demo
```python
import gzip
import cursed_format as bfk

obj = {"secure": "data"}
enc = bfk.encode_object(obj, compress=True, use_hmac=True)

# Tamper with the data
text = gzip.decompress(enc).decode("utf-8")
tampered = text.replace(".", "+", 1)
enc2 = gzip.compress(tampered.encode())

try:
    bfk.decode_object(enc2)
except ValueError as e:
    print(f"Tamper detected: {e}")
```

---

# 🔐 Strategy Comparison

| Strategy         | Speed   | Output Size | Notes                 |
|------------------|---------|-------------|-----------------------|
| stock            | slow    | big         | naive                 |
| cached           | fast    | small       | reuses cells          |
| cached_heuristic | fastest | smallest    | caches frequent bytes |

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
