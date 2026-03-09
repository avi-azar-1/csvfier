# csvfier

Convert **any file** to a valid CSV and back — losslessly.  
Pass code (or any text) through a medium that only allows `.csv` files.

## Usage

```bash
# Encode a file into CSV
python csvfier.py encode myfile.py              # → myfile.py.csv
python csvfier.py encode myfile.py -o out.csv   # → out.csv

# Decode back to original
python csvfier.py decode out.csv                # → restores original filename
python csvfier.py decode out.csv -o restored.py # → restored.py
```

## How it works

1. **Encode**: reads the file as raw bytes, base64-encodes it, and writes a CSV with metadata (filename, SHA-256 checksum, byte size) and chunked data rows.
2. **Decode**: reads the CSV, reassembles the base64 data, verifies checksum + size, and writes the exact original bytes.

The round-trip is **byte-identical** — line endings, trailing newlines, and encoding are all preserved exactly.

## Run tests

```bash
python -m pytest tests/test_csvfier.py -v
```
