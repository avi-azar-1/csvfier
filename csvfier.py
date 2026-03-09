#!/usr/bin/env python3
"""
csvfier — Convert any file to valid CSV and back, losslessly.

Usage:
    python csvfier.py encode <input-file> [-o output.csv]
    python csvfier.py decode <input.csv>  [-o output-file]

The generated CSV has this schema (3 columns: type, key, value):

    type,key,value
    meta,filename,<original basename>
    meta,checksum,sha256:<hex digest>
    meta,size,<byte count>
    data,0,<base64 chunk>
    data,1,<base64 chunk>
    ...

Encoding is base64 so the round-trip is byte-identical for any file.
"""

import argparse
import base64
import csv
import hashlib
import os
import sys
from pathlib import Path

# How many characters per base64 chunk row (76 = MIME standard line length)
CHUNK_SIZE = 76


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def encode(input_path: str, output_path: str) -> None:
    """Read *input_path* as raw bytes, write a csvfier CSV to *output_path*."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    raw = input_path.read_bytes()

    filename = input_path.name
    checksum = "sha256:" + hashlib.sha256(raw).hexdigest()
    size = str(len(raw))

    b64 = base64.b64encode(raw).decode("ascii")

    # Split into fixed-size chunks
    chunks = [b64[i : i + CHUNK_SIZE] for i in range(0, len(b64), CHUNK_SIZE)] if b64 else []

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Metadata rows
        writer.writerow(["meta", "filename", filename])
        writer.writerow(["meta", "checksum", checksum])
        writer.writerow(["meta", "size", size])
        # Data rows
        for idx, chunk in enumerate(chunks):
            writer.writerow(["data", str(idx), chunk])


def decode(input_path: str, output_path: str | None) -> None:
    """Read a csvfier CSV from *input_path*, reconstruct the original file.

    If *output_path* is ``None``, the original filename from metadata is used
    and the file is written to the current working directory.
    """
    input_path = Path(input_path)

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty — not a valid csvfier file")

    # Parse metadata
    meta: dict[str, str] = {}
    data_chunks: dict[int, str] = {}

    for row in rows:
        if len(row) != 3:
            raise ValueError(f"Invalid row (expected 3 columns): {row!r}")
        rtype, key, value = row
        if rtype == "meta":
            meta[key] = value
        elif rtype == "data":
            data_chunks[int(key)] = value
        else:
            raise ValueError(f"Unknown row type: {rtype!r}")

    # Validate required metadata
    for required in ("filename", "checksum", "size"):
        if required not in meta:
            raise ValueError(f"Missing required metadata: {required}")

    # Reassemble base64 string in order
    b64 = "".join(data_chunks[i] for i in range(len(data_chunks)))

    # Decode
    raw = base64.b64decode(b64)

    # Verify size
    expected_size = int(meta["size"])
    if len(raw) != expected_size:
        raise ValueError(
            f"Size mismatch: metadata says {expected_size} bytes, "
            f"decoded {len(raw)} bytes"
        )

    # Verify checksum
    expected_checksum = meta["checksum"]
    actual_checksum = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual_checksum != expected_checksum:
        raise ValueError(
            f"Checksum mismatch — file is corrupted or tampered.\n"
            f"  expected: {expected_checksum}\n"
            f"  actual:   {actual_checksum}"
        )

    # Determine output path
    if output_path is None:
        output_path = Path.cwd() / meta["filename"]
    else:
        output_path = Path(output_path)

    output_path.write_bytes(raw)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csvfier",
        description="Convert any file to valid CSV and back, losslessly.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # encode
    enc = sub.add_parser("encode", help="Convert a file to a csvfier CSV")
    enc.add_argument("input", help="Path to the file to encode")
    enc.add_argument("-o", "--output", default=None, help="Output CSV path (default: <input>.csv)")

    # decode
    dec = sub.add_parser("decode", help="Recover the original file from a csvfier CSV")
    dec.add_argument("input", help="Path to the csvfier CSV file")
    dec.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path (default: use original filename from metadata)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "encode":
            output = args.output or (args.input + ".csv")
            encode(args.input, output)
            print(f"Encoded -> {output}")

        elif args.command == "decode":
            decode(args.input, args.output)
            target = args.output or "(original filename)"
            print(f"Decoded -> {target}")

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
