"""Add zip fixture to tests/fixtures/sample.zip"""
import zipfile
import io
from pathlib import Path

fixtures = Path(__file__).parent / "fixtures"

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("hello.txt", "Hello from inside the zip!\nLine two.\n")
    zf.writestr("subdir/code.py", "def foo():\n    return 'bar'\n")
    zf.writestr("data.csv", "col1,col2\n\"val,1\",val2\n")

(fixtures / "sample.zip").write_bytes(buf.getvalue())
print(f"Created sample.zip: {(fixtures / 'sample.zip').stat().st_size} bytes")

# Verify it's a valid zip
with zipfile.ZipFile(fixtures / "sample.zip") as zf:
    print("Zip contents:", zf.namelist())
