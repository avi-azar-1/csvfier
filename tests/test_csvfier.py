"""
test_csvfier.py
===============
Full test suite for csvfier.py.

Run with:
    pytest tests/test_csvfier.py -v

The tests are written so that they will FAIL until csvfier.py is implemented,
clearly describing the expected contract of encode() and decode().

All round-trip tests follow the same pattern:
    1. Read the fixture file as raw bytes (ground truth)
    2. Call encode() → produce a .csv file
    3. Validate the CSV structure
    4. Call decode() on the .csv → produce a recovered file
    5. Assert recovered bytes == original bytes  (byte-identical)
"""

import csv
import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"
# csvfier.py lives one level above the tests/ directory
CSVFIER = Path(__file__).parent.parent / "csvfier.py"


def fixture(name: str) -> Path:
    return FIXTURES / name


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Import the module under test.
# All tests below will be skipped (not failed) if csvfier.py doesn't exist yet.
# ---------------------------------------------------------------------------

try:
    import importlib.util

    spec = importlib.util.spec_from_file_location("csvfier", CSVFIER)
    csvfier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(csvfier)
    MODULE_AVAILABLE = True
except (FileNotFoundError, AttributeError):
    csvfier = None
    MODULE_AVAILABLE = False


def require_module(fn):
    """Decorator: skip test if csvfier.py is not yet available."""
    return pytest.mark.skipif(
        not MODULE_AVAILABLE,
        reason="csvfier.py not yet implemented",
    )(fn)


# ---------------------------------------------------------------------------
# Helper: run encode + decode and return recovered bytes
# ---------------------------------------------------------------------------


def round_trip(input_path: Path, tmp_path: Path) -> bytes:
    """
    Encode input_path → tmp CSV, then decode that CSV → recovered file.
    Returns the recovered bytes.
    """
    csv_path = tmp_path / (input_path.name + ".csv")
    recovered_path = tmp_path / ("recovered_" + input_path.name)

    csvfier.encode(str(input_path), str(csv_path))
    csvfier.decode(str(csv_path), str(recovered_path))

    return recovered_path.read_bytes()


# ---------------------------------------------------------------------------
# CSV Structure Validator
# ---------------------------------------------------------------------------


def assert_valid_csv_structure(csv_path: Path):
    """
    Check that the generated CSV:
    - Is parseable by the standard csv module without errors.
    - Has exactly 3 columns per row (type, key, value).
    - Starts with the required metadata rows: filename, checksum, size.
    - Has at least one data row (unless source file was empty).
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) >= 3, "CSV must have at least 3 rows (meta: filename, checksum, size)"

    for i, row in enumerate(rows):
        assert len(row) == 3, (
            f"Row {i} has {len(row)} columns, expected 3. Row content: {row!r}"
        )

    # Check metadata rows
    meta_rows = {row[1]: row[2] for row in rows if row[0] == "meta"}
    assert "filename" in meta_rows, "Missing meta row: filename"
    assert "checksum" in meta_rows, "Missing meta row: checksum"
    assert "size" in meta_rows, "Missing meta row: size"

    # size must be a non-negative integer
    assert meta_rows["size"].isdigit(), f"size metadata is not a digit: {meta_rows['size']!r}"

    # checksum must start with 'sha256:'
    assert meta_rows["checksum"].startswith("sha256:"), (
        f"checksum must be prefixed with 'sha256:', got: {meta_rows['checksum']!r}"
    )

    # data rows must have sequential integer keys starting at 0
    data_rows = [row for row in rows if row[0] == "data"]
    for expected_idx, row in enumerate(data_rows):
        assert row[1] == str(expected_idx), (
            f"data row key mismatch: expected '{expected_idx}', got '{row[1]}'"
        )


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestRoundTrips:

    @require_module
    def test_simple_text(self, tmp_path):
        """Plain text file with 3 lines and a trailing newline."""
        original = read_bytes(fixture("simple.txt"))
        recovered = round_trip(fixture("simple.txt"), tmp_path)
        assert recovered == original, "simple.txt: byte-identical round-trip failed"

    @require_module
    def test_python_source_code(self, tmp_path):
        """Python source with quotes, apostrophes, hashes, indentation, docstrings."""
        original = read_bytes(fixture("code.py"))
        recovered = round_trip(fixture("code.py"), tmp_path)
        assert recovered == original, "code.py: byte-identical round-trip failed"

    @require_module
    def test_commas_and_quotes(self, tmp_path):
        """File with CSV-special chars: commas, double quotes, injection prefixes."""
        original = read_bytes(fixture("commas_and_quotes.txt"))
        recovered = round_trip(fixture("commas_and_quotes.txt"), tmp_path)
        assert recovered == original, "commas_and_quotes.txt: byte-identical round-trip failed"

    @require_module
    def test_empty_file(self, tmp_path):
        """Zero-byte file must survive the round-trip."""
        original = read_bytes(fixture("empty.txt"))
        assert original == b"", "Fixture sanity: empty.txt should be 0 bytes"
        recovered = round_trip(fixture("empty.txt"), tmp_path)
        assert recovered == original, "empty.txt: byte-identical round-trip failed"

    @require_module
    def test_no_trailing_newline(self, tmp_path):
        """File that does NOT end with a newline character."""
        original = read_bytes(fixture("no_trailing_newline.txt"))
        assert original[-1:] != b"\n", "Fixture sanity: file should NOT end with LF"
        recovered = round_trip(fixture("no_trailing_newline.txt"), tmp_path)
        assert recovered == original, "no_trailing_newline.txt: byte-identical round-trip failed"
        assert recovered[-1:] != b"\n", "Recovered file should still NOT end with LF"

    @require_module
    def test_crlf_line_endings(self, tmp_path):
        """File with Windows CRLF (\\r\\n) line endings — must be preserved exactly."""
        original = read_bytes(fixture("crlf.txt"))
        assert b"\r\n" in original, "Fixture sanity: crlf.txt should contain CRLF sequences"
        recovered = round_trip(fixture("crlf.txt"), tmp_path)
        assert recovered == original, "crlf.txt: byte-identical round-trip failed"
        assert b"\r\n" in recovered, "Recovered file should still contain CRLF sequences"

    @require_module
    def test_unicode(self, tmp_path):
        """Multi-byte UTF-8: CJK, Arabic, emoji, math symbols."""
        original = read_bytes(fixture("unicode.txt"))
        recovered = round_trip(fixture("unicode.txt"), tmp_path)
        assert recovered == original, "unicode.txt: byte-identical round-trip failed"

    @require_module
    def test_zip_file(self, tmp_path):
        """Binary zip file — magic bytes, compressed data, and internal structure preserved."""
        original = read_bytes(fixture("sample.zip"))
        # Confirm fixture is a real zip (magic bytes PK\x03\x04)
        assert original[:4] == b"PK\x03\x04", "Fixture sanity: sample.zip must start with PK magic bytes"
        recovered = round_trip(fixture("sample.zip"), tmp_path)
        assert recovered == original, "sample.zip: byte-identical round-trip failed"
        # Confirm the recovered bytes are still a readable zip
        with zipfile.ZipFile(tmp_path / "recovered_sample.zip") as zf:
            names = zf.namelist()
        assert "hello.txt" in names, "Recovered zip should contain hello.txt"
        assert "subdir/code.py" in names, "Recovered zip should contain subdir/code.py"
        assert "data.csv" in names, "Recovered zip should contain data.csv"


# ---------------------------------------------------------------------------
# CSV structure tests
# ---------------------------------------------------------------------------


class TestCSVStructure:

    @require_module
    def test_csv_is_parseable(self, tmp_path):
        """The generated CSV must be parseable by Python's standard csv module."""
        csv_path = tmp_path / "code.csv"
        csvfier.encode(str(fixture("code.py")), str(csv_path))
        # Will raise csv.Error if malformed
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) > 0

    @require_module
    def test_csv_structure_simple(self, tmp_path):
        """simple.txt → CSV must have correct structure with all metadata."""
        csv_path = tmp_path / "simple.csv"
        csvfier.encode(str(fixture("simple.txt")), str(csv_path))
        assert_valid_csv_structure(csv_path)

    @require_module
    def test_csv_structure_code(self, tmp_path):
        """code.py → CSV must have correct structure with all metadata."""
        csv_path = tmp_path / "code.csv"
        csvfier.encode(str(fixture("code.py")), str(csv_path))
        assert_valid_csv_structure(csv_path)

    @require_module
    def test_csv_structure_empty(self, tmp_path):
        """empty.txt → CSV must still have the 3 metadata rows, 0 data rows."""
        csv_path = tmp_path / "empty.csv"
        csvfier.encode(str(fixture("empty.txt")), str(csv_path))
        assert_valid_csv_structure(csv_path)

    @require_module
    def test_csv_metadata_filename(self, tmp_path):
        """The filename stored in metadata must match the original file's basename."""
        csv_path = tmp_path / "simple.csv"
        csvfier.encode(str(fixture("simple.txt")), str(csv_path))

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        meta = {r[1]: r[2] for r in rows if r[0] == "meta"}
        assert meta["filename"] == "simple.txt"

    @require_module
    def test_csv_metadata_size(self, tmp_path):
        """The size in metadata must match the actual byte size of the original file."""
        path = fixture("code.py")
        csv_path = tmp_path / "code.csv"
        csvfier.encode(str(path), str(csv_path))

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        meta = {r[1]: r[2] for r in rows if r[0] == "meta"}
        assert int(meta["size"]) == path.stat().st_size

    @require_module
    def test_csv_metadata_checksum(self, tmp_path):
        """The SHA-256 checksum in metadata must match the original file content."""
        path = fixture("code.py")
        csv_path = tmp_path / "code.csv"
        csvfier.encode(str(path), str(csv_path))

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        meta = {r[1]: r[2] for r in rows if r[0] == "meta"}

        expected = "sha256:" + sha256(read_bytes(path))
        assert meta["checksum"] == expected


# ---------------------------------------------------------------------------
# Integrity / tamper detection
# ---------------------------------------------------------------------------


class TestIntegrity:

    @require_module
    def test_checksum_mismatch_raises(self, tmp_path):
        """
        If the CSV data is tampered (a data chunk is altered),
        decode() must raise an exception (not silently produce wrong output).
        """
        csv_path = tmp_path / "tampered.csv"
        csvfier.encode(str(fixture("simple.txt")), str(csv_path))

        # Read all rows, corrupt the value of the first data row
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        for i, row in enumerate(rows):
            if row[0] == "data":
                # Flip a character in the base64 data
                original_val = row[2]
                corrupted = original_val[:-4] + "XXXX"
                rows[i] = [row[0], row[1], corrupted]
                break

        tampered_path = tmp_path / "tampered_written.csv"
        with open(tampered_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        with pytest.raises(Exception, match=r"[Cc]hecksum|[Cc]orrupt|[Ii]ntegrity|[Mm]ismatch"):
            csvfier.decode(str(tampered_path), str(tmp_path / "should_not_exist.txt"))

    @require_module
    def test_size_mismatch_raises(self, tmp_path):
        """
        If the size metadata is tampered, decode() must raise, not silently pass.
        """
        csv_path = tmp_path / "tampered_size.csv"
        csvfier.encode(str(fixture("simple.txt")), str(csv_path))

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        for i, row in enumerate(rows):
            if row[0] == "meta" and row[1] == "size":
                rows[i] = [row[0], row[1], "999999"]
                break

        tampered_path = tmp_path / "tampered_size_written.csv"
        with open(tampered_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        with pytest.raises(Exception):
            csvfier.decode(str(tampered_path), str(tmp_path / "should_not_exist.txt"))


# ---------------------------------------------------------------------------
# Decode output path tests
# ---------------------------------------------------------------------------


class TestDecodeOutputPath:

    @require_module
    def test_decode_with_explicit_output(self, tmp_path):
        """decode() with an explicit output path should write to that exact path."""
        csv_path = tmp_path / "simple.csv"
        out_path = tmp_path / "my_custom_name.txt"
        csvfier.encode(str(fixture("simple.txt")), str(csv_path))
        csvfier.decode(str(csv_path), str(out_path))
        assert out_path.exists(), "Output file should exist at the specified path"
        assert out_path.read_bytes() == read_bytes(fixture("simple.txt"))

    @require_module
    def test_decode_without_output_uses_metadata_filename(self, tmp_path):
        """
        When no output path is given, decode() should write to CWD/<original-filename>.
        We test this by calling decode() with output=None (or omitting it).
        """
        csv_path = tmp_path / "simple.csv"
        csvfier.encode(str(fixture("simple.txt")), str(csv_path))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Pass None or omit the output argument — implementation decides
            csvfier.decode(str(csv_path), None)
            recovered = (tmp_path / "simple.txt").read_bytes()
            assert recovered == read_bytes(fixture("simple.txt"))
        finally:
            os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# CLI tests (subprocess — end-to-end)
# ---------------------------------------------------------------------------


class TestCLI:

    @pytest.mark.skipif(not CSVFIER.exists(), reason="csvfier.py not yet implemented")
    def test_cli_encode_decode_round_trip(self, tmp_path):
        """End-to-end CLI: python csvfier.py encode ... | decode ... == original."""
        input_file = fixture("code.py")
        csv_output = tmp_path / "code.csv"
        recovered = tmp_path / "code_recovered.py"

        # Encode
        result = subprocess.run(
            [sys.executable, str(CSVFIER), "encode", str(input_file), "-o", str(csv_output)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"encode failed:\n{result.stderr}"
        assert csv_output.exists(), "CSV output file not created"

        # Decode
        result = subprocess.run(
            [sys.executable, str(CSVFIER), "decode", str(csv_output), "-o", str(recovered)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"decode failed:\n{result.stderr}"
        assert recovered.exists(), "Recovered file not created"

        assert recovered.read_bytes() == input_file.read_bytes(), "CLI round-trip not byte-identical"

    @pytest.mark.skipif(not CSVFIER.exists(), reason="csvfier.py not yet implemented")
    def test_cli_default_output_name(self, tmp_path):
        """CLI encode with no -o should default to <filename>.csv next to source."""
        src = tmp_path / "hello.txt"
        src.write_bytes(b"hello world\n")
        expected_csv = tmp_path / "hello.txt.csv"

        result = subprocess.run(
            [sys.executable, str(CSVFIER), "encode", str(src)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"encode failed:\n{result.stderr}"
        assert expected_csv.exists(), f"Expected default CSV at {expected_csv}"

    @pytest.mark.skipif(not CSVFIER.exists(), reason="csvfier.py not yet implemented")
    def test_cli_bad_csv_exits_nonzero(self, tmp_path):
        """Decoding a non-CSV file should exit with a non-zero return code."""
        bad_file = tmp_path / "bad.csv"
        bad_file.write_text("this is not a valid csvfier csv\n")

        result = subprocess.run(
            [sys.executable, str(CSVFIER), "decode", str(bad_file), "-o", str(tmp_path / "out.txt")],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "decode of invalid CSV should exit non-zero"


# ---------------------------------------------------------------------------
# Fixture sanity checks (always run — no csvfier.py required)
# ---------------------------------------------------------------------------


class TestFixtureSanity:
    """Verify the fixture files themselves are correct before relying on them."""

    def test_simple_txt_exists_and_has_content(self):
        assert fixture("simple.txt").exists()
        assert fixture("simple.txt").stat().st_size > 0
        data = read_bytes(fixture("simple.txt"))
        assert data.endswith(b"\n"), "simple.txt should end with a newline"

    def test_code_py_exists_and_is_valid_python(self):
        assert fixture("code.py").exists()
        import ast
        src = fixture("code.py").read_text(encoding="utf-8")
        ast.parse(src)  # Raises SyntaxError if invalid

    def test_commas_and_quotes_contains_special_chars(self):
        data = read_bytes(fixture("commas_and_quotes.txt"))
        assert b"," in data
        assert b'"' in data

    def test_empty_txt_is_zero_bytes(self):
        assert fixture("empty.txt").stat().st_size == 0

    def test_no_trailing_newline_exists_and_no_final_lf(self):
        assert fixture("no_trailing_newline.txt").exists()
        data = read_bytes(fixture("no_trailing_newline.txt"))
        assert len(data) > 0
        assert data[-1] != 10, "no_trailing_newline.txt must not end with LF (0x0A)"

    def test_crlf_exists_and_has_crlf(self):
        assert fixture("crlf.txt").exists()
        data = read_bytes(fixture("crlf.txt"))
        assert b"\r\n" in data, "crlf.txt must contain CRLF sequences"
        assert b"\n" in data  # will also be true, just confirm file has content

    def test_unicode_txt_contains_multibyte_chars(self):
        assert fixture("unicode.txt").exists()
        data = read_bytes(fixture("unicode.txt"))
        # UTF-8 multi-byte chars have bytes > 0x7F
        assert any(b > 0x7F for b in data), "unicode.txt should contain multi-byte UTF-8 chars"

    def test_sample_zip_is_valid(self):
        assert fixture("sample.zip").exists()
        data = read_bytes(fixture("sample.zip"))
        # ZIP magic bytes: PK\x03\x04
        assert data[:4] == b"PK\x03\x04", "sample.zip must start with ZIP magic bytes"
        with zipfile.ZipFile(fixture("sample.zip")) as zf:
            names = zf.namelist()
        assert "hello.txt" in names
        assert "subdir/code.py" in names
        assert "data.csv" in names
