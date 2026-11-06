# mini_mime_content_transfer

A small, dependency-free codec for the seven MIME content-transfer-encodings.

## Usage

```python
from mini_mime_content_transfer import encode, decode, ENCODINGS

raw = b"any carnal pleasure."
encoded = encode(raw, "base64")
assert encoded == b"YW55IGNhcm5hbCBwbGVhc3VyZS4="
assert decode(encoded, "base64") == raw

# The two inverse names swap the direction of their forward counterpart.
assert encode(encoded, "base64-inverse") == raw
assert decode(raw, "base64-inverse") == encoded

print(ENCODINGS)
# ('7bit', '8bit', 'binary', 'base64', 'quoted-printable',
#  'base64-inverse', 'quoted-printable-inverse')
```

## Why this exists

MIME bodies carry a `Content-Transfer-Encoding` header that names one of
several transforms.  The standard library gives you `base64` and `quopri`,
but not a single entry point that dispatches on the header value, and it does
not define the `-inverse` spellings that appear in some MIME profiles.

This library provides one `encode(data, encoding)` / `decode(data, encoding)`
pair covering all seven names.  The trade-off is deliberate: the three
identity encodings (`7bit`, `8bit`, `binary`) are treated as pure identity
transforms.  A stricter implementation would validate that a `7bit` body
contains no bytes above 0x7F, but that validation belongs to a policy layer,
not to a codec, and rejecting such bodies here would make round-tripping
impossible for the many real-world messages that mislabel their encoding.

## The awkward edge

The `-inverse` names are not defined by RFC 2045.  This library chooses one
interpretation: `encode(data, "base64-inverse")` is exactly
`decode(data, "base64")`, and `decode(data, "base64-inverse")` is exactly
`encode(data, "base64")`.  The same rule applies to
`quoted-printable-inverse`.  If your application expects a different
meaning, do not use the inverse names; call the forward codec directly.

## Exports

- `encode(data: bytes, encoding: str) -> bytes`
- `decode(data: bytes, encoding: str) -> bytes`
- `ContentTransferEncodingError` (subclass of `ValueError`)
- `ENCODINGS` (tuple of the seven supported names)
