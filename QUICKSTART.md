# 🚀 BFK1 Quick Start — 5 Minute Demo

*Get started with Brainfuck JSON encoding in under 5 minutes!*

---

## 🎯 What You'll Learn

1. Encode a simple JSON object to Brainfuck
2. Decode it back to JSON
3. Try it in an online Brainfuck interpreter
4. Work with real test data

---

## 📦 Prerequisites

```bash
git clone https://github.com/CSonTi04/json-bf
cd json-bf
```

Requires **Python ≥ 3.9** (no extra packages needed!)

---

## 🏃 Quick Demo (2 minutes)

### Step 1: Encode a simple JSON

```bash
python cursed_format.py encode-json .\test_data\1KB.json --no-compress
```

This creates `.\test_data\1KB.json.bf` — a plain text Brainfuck program!

### Step 2: Look at the Brainfuck code

```bash
type .\test_data\1KB.json.bf
```

You'll see something like:
```brainfuck
/// BFK1 JSON Brainfuck encoded
/// MAC hmac-sha256:...
[-]>[-]+++++++++[<++++++++++>-]<+++++...
```

### Step 3: Decode it back

```bash
python cursed_format.py decode-json .\test_data\1KB.json.bf
```

This creates `.\test_data\1KB.json.bf.json` — your original JSON is back!

### Step 4: Verify it matches

```bash
# For PowerShell:
Compare-Object (Get-Content .\test_data\1KB.json) (Get-Content .\test_data\1KB.json.bf.json)
# No output means files are identical!

# For Command Prompt (cmd):
---

## 🌐 Try It Online

Want to see Brainfuck in action without installing anything?

1. **Get the Brainfuck code** from your `.bf` file (copy everything after the `///` headers)
2. **Visit the online interpreter**: [https://copy.sh/brainfuck/](https://copy.sh/brainfuck/)
3. **Paste the code** and hit "Run"
4. **Watch** as it outputs your JSON character by character!

### Quick Online Example

Encode a tiny JSON:
```bash
python cursed_format.py encode '{"x":1}' --no-mac
```

Copy the Brainfuck output (skip the `///` lines), paste into [https://copy.sh/brainfuck/](https://copy.sh/brainfuck/), and hit Run!

---

## 🧪 Working with Real Test Data

### Using Provided Test Files

We include several test files from **1KB to 5MB**:

```bash
# Encode the minified 1KB JSON
python cursed_format.py encode-json .\test_data\1KB-min.json

# Creates: .\test_data\1KB-min.json.bf.gz (compressed)
```

### Get More Test Data

Need more JSON samples? Check out:
**[Microsoft Edge JSON Dummy Data](https://microsoftedge.github.io/Demos/json-dummy-data/)**

Download any JSON, save it to `.\test_data\`, and encode it:

```bash
# Example: Save a sample as custom.json
python cursed_format.py encode-json .\test_data\custom.json
```

---

## 🎨 Fun Experiments (3 minutes)

### Experiment 1: Compare Compression

```bash
# Encode with compression (default)
python cursed_format.py encode-json .\test_data\1KB.json
# Result: .\test_data\1KB.json.bf.gz

# Encode without compression
python cursed_format.py encode-json .\test_data\1KB.json --no-compress
# Result: .\test_data\1KB.json.bf

# Compare file sizes
dir .\test_data\1KB.json*
```

Notice how `.bf.gz` is much smaller than `.bf`!

### Experiment 2: Try Different Strategies

```bash
# Stock strategy (naive, slower)
python cursed_format.py encode "test" --strategy stock

# Cached strategy (smart, faster)
python cursed_format.py encode "test" --strategy cached

# Cached heuristic (smartest, fastest)
python cursed_format.py encode "test" --strategy cached_heuristic
```

Watch how the Brainfuck code changes!

### Experiment 3: Security Check

```bash
# Encode with HMAC protection
python cursed_format.py encode-json .\test_data\1KB.json

# Try to manually tamper with the file
# (Open .\test_data\1KB.json.bf.gz in a hex editor and change a byte)

# Decode — it should fail with "MAC validation failed"
python cursed_format.py decode-json .\test_data\1KB.json.bf.gz
```

---

## 📊 Size Comparison Table

Here's what you can expect with our test files:

| Original File | Size    | .bf.gz Size | .gz Size (direct) | BFK1 Overhead |
|---------------|---------|-------------|-------------------|---------------|
| 1KB.json      | ~1 KB   | ~1.5 KB     | ~400 B            | ~3.75x        |
| 1KB-min.json  | ~1 KB   | ~1.4 KB     | ~350 B            | ~4x           |
| 64KB.json     | ~64 KB  | ~50 KB      | ~12 KB            | ~4x           |
| 1MB.json      | ~1 MB   | ~750 KB     | ~180 KB           | ~4x           |

*Note: BFK1 is intentionally inefficient for fun — don't use it in production!*

---

## 🎯 Real-World Example

### Scenario: Share JSON as Brainfuck

```bash
# 1. Create a simple JSON file
'{"name":"Alice","age":30}' | Out-File -Encoding utf8NoBOM demo.json

# 2. Encode it (compressed)
python cursed_format.py encode-json demo.json

# 3. Share the .bf.gz file
# (It's tamper-proof with HMAC!)

# 4. Recipient decodes it
python cursed_format.py decode-json demo.json.bf.gz

# 5. Verify the output
type demo.json.bf.gz.json
```

---

## 🐍 Python API Quick Example

```python
import cursed_format as bfk
import json

# Encode
data = {"hello": "world", "numbers": [1, 2, 3]}
encoded = bfk.encode_object(data, compress=True)

# Save
with open("output.bf.gz", "wb") as f:
    f.write(encoded)

# Load and decode
with open("output.bf.gz", "rb") as f:
    decoded = bfk.decode_object(f.read())

print(decoded)  # {"hello": "world", "numbers": [1, 2, 3]}
```

---

## 🎓 Next Steps

1. **Read the full README**: See `README.md` for all features and options
2. **Try larger files**: Encode `64KB.json`, `128KB.json`, etc.
3. **Experiment with strategies**: Compare `stock`, `cached`, and `cached_heuristic`
4. **Test security**: Try tampering with HMAC-protected files
5. **Benchmark performance**: Time encoding/decoding on large files

---

## 🙏 Credits & Resources

- **Online Brainfuck Interpreter**: [https://copy.sh/brainfuck/](https://copy.sh/brainfuck/)
- **Test Data Source**: [Microsoft Edge JSON Dummy Data](https://microsoftedge.github.io/Demos/json-dummy-data/)
- **Brainfuck Language**: [Wikipedia](https://en.wikipedia.org/wiki/Brainfuck)

---

## 💡 Tips

- **Start small**: Use 1KB files before jumping to 5MB
- **Use `--no-compress`** to see raw Brainfuck (great for learning)
- **Try `--verbose`** to see what's happening during encoding/decoding
- **Use `--pretty`** when decoding to get formatted JSON output
- **Check file sizes** with `dir` (Windows) or `ls -lh` (Linux/Mac)

---

## ❓ Troubleshooting

**Q: Encoding is slow**  
A: Use `--strategy cached_heuristic` for best performance

**Q: Decode fails with "MAC validation failed"**  
A: File was tampered with, or use `--no-mac` during encoding if you don't need security

**Q: Want to see the Brainfuck code?**  
A: Use `--no-compress` to get a `.bf` text file instead of `.bf.gz`

**Q: Output file already exists**  
A: Specify custom output with `--output myfile.bf.gz`

---

## 🎉 You're Ready!

Now you know how to:
✅ Encode JSON to Brainfuck  
✅ Decode Brainfuck back to JSON  
✅ Try it online  
✅ Work with test data  

Go forth and confuse your colleagues! 😈

For more advanced usage, see the full [README.md](README.md).

