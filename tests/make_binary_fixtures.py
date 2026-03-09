"""Generate binary fixtures that can't be created with plain text editors."""
with open('tests/fixtures/no_trailing_newline.txt', 'wb') as f:
    f.write(b'First line\nSecond line\nThird line -- no newline after this')

with open('tests/fixtures/crlf.txt', 'wb') as f:
    f.write(b'Line one\r\nLine two\r\nLine three\r\nLine, with a comma\r\n"Quoted line"\r\n')

import os
print('no_trailing_newline.txt:', os.path.getsize('tests/fixtures/no_trailing_newline.txt'), 'bytes')
print('crlf.txt:', os.path.getsize('tests/fixtures/crlf.txt'), 'bytes')

with open('tests/fixtures/no_trailing_newline.txt', 'rb') as f:
    data = f.read()
print('Ends with LF:', data[-1] == 10)
print('Done.')
