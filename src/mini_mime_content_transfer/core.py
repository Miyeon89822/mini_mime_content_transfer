"""MIME content-transfer-encoding codec.

The seven canonical MIME content-transfer-encodings are:

    7bit, 8bit, binary, base64, quoted-printable

plus the two "inverse" names that appear in some MIME profiles:

    base64-inverse, quoted-printable-inverse

This module implements all seven.  The inverse encodings are defined here as
the exact inverse of the corresponding forward encoding: ``decode`` of the
plain name and ``encode`` of the inverse name produce the same bytes, and
vice versa.  This is a deliberate, single interpretation of an otherwise
ambiguous corner of the MIME specifications.

Design notes
------------
* ``7bit`` and ``8bit`` are identity transforms.  They are distinct names
  because MIME uses them to declare the byte range of the body, but for the
  purposes of a codec they do not alter the payload.
* ``binary`` is also an identity transform.  It declares that the body may
  contain arbitrary bytes and no line-length limit applies.
* ``base64`` and ``quoted-printable`` follow RFC 2045.  The decoders are
  lenient about whitespace and missing padding where that does not create
  ambiguity, and strict about genuinely malformed input.

All functions accept and return ``bytes``.  Text encodings are not applied
here; callers that need text should encode to UTF-8 (or another charset)
before calling into this module.
"""

from __future__ import annotations

import base64
import binascii
import quopri
from typing import Callable, Dict, Final


class ContentTransferEncodingError(ValueError):
    """Raised when a payload cannot be encoded or decoded as requested."""


# The canonical names.  The two ``-inverse`` names are handled by swapping
# the direction of the corresponding forward codec, which is why they are
# not listed as separate entries in this mapping.
ENCODINGS: Final[tuple[str, ...]] = (
    "7bit",
    "8bit",
    "binary",
    "base64",
    "quoted-printable",
    "base64-inverse",
    "quoted-printable-inverse",
)


def _identity_encode(data: bytes) -> bytes:
    return data


def _identity_decode(data: bytes) -> bytes:
    return data


def _base64_encode(data: bytes) -> bytes:
    # RFC 2045 requires line breaks at most 76 characters apart.  The
    # standard library's ``b64encode`` does not insert them, so we do it
    # ourselves.  ``validate=False`` is the default and accepts the
    # canonical alphabet only; that is what we want.
    encoded = base64.b64encode(data)
    return _wrap_base64(encoded)


def _wrap_base64(encoded: bytes) -> bytes:
    lines = [encoded[i : i + 76] for i in range(0, len(encoded), 76)]
    return b"\r\n".join(lines)


def _base64_decode(data: bytes) -> bytes:
    # Strip ASCII whitespace first: MIME base64 bodies are commonly wrapped
    # with CRLF, and some producers use spaces or tabs.  ``b64decode`` with
    # ``validate=False`` ignores non-alphabet characters, but we want to
    # reject genuinely invalid input, so we only remove whitespace.
    cleaned = bytes(b for b in data if b not in b" \t\r\n")
    try:
        return base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ContentTransferEncodingError(str(exc)) from exc


def _quoted_printable_encode(data: bytes) -> bytes:
    # ``quopri.encodestring`` already handles line wrapping and soft breaks.
    # We pass ``quotetabs=False`` so that tabs are not needlessly encoded;
    # RFC 2045 permits literal tabs inside a line.
    return quopri.encodestring(data, quotetabs=False)


def _quoted_printable_decode(data: bytes) -> bytes:
    try:
        return quopri.decodestring(data)
    except (binascii.Error, ValueError) as exc:
        raise ContentTransferEncodingError(str(exc)) from exc


# Forward codecs, keyed by the canonical name.  The inverse names are
# resolved by looking up the forward codec and swapping encode/decode.
_FORWARD_ENCODERS: Dict[str, Callable[[bytes], bytes]] = {
    "7bit": _identity_encode,
    "8bit": _identity_encode,
    "binary": _identity_encode,
    "base64": _base64_encode,
    "quoted-printable": _quoted_printable_encode,
}

_FORWARD_DECODERS: Dict[str, Callable[[bytes], bytes]] = {
    "7bit": _identity_decode,
    "8bit": _identity_decode,
    "binary": _identity_decode,
    "base64": _base64_decode,
    "quoted-printable": _quoted_printable_decode,
}


def _resolve(name: str) -> tuple[str, bool]:
    """Return ``(forward_name, inverse)`` for a user-supplied encoding name.

    The ``-inverse`` suffix is stripped and the resulting forward name is
    returned together with a flag indicating that the direction should be
    swapped.  Unknown names raise ``ContentTransferEncodingError``.
    """
    if name.endswith("-inverse"):
        forward = name[: -len("-inverse")]
        if forward not in _FORWARD_ENCODERS:
            raise ContentTransferEncodingError(
                f"unknown content-transfer-encoding: {name!r}"
            )
        return forward, True
    if name not in _FORWARD_ENCODERS:
        raise ContentTransferEncodingError(
            f"unknown content-transfer-encoding: {name!r}"
        )
    return name, False


def encode(data: bytes, encoding: str) -> bytes:
    """Encode *data* using the named MIME content-transfer-encoding.

    Parameters
    ----------
    data:
        The raw bytes to encode.
    encoding:
        One of the names in :data:`ENCODINGS`.

    Returns
    -------
    bytes
        The encoded payload.  Identity encodings return *data* unchanged.

    Raises
    ------
    ContentTransferEncodingError
        If *encoding* is not a recognised name.
    """
    forward, inverse = _resolve(encoding)
    if inverse:
        return _FORWARD_DECODERS[forward](data)
    return _FORWARD_ENCODERS[forward](data)


def decode(data: bytes, encoding: str) -> bytes:
    """Decode *data* using the named MIME content-transfer-encoding.

    This is the inverse of :func:`encode` for every supported name.

    Raises
    ------
    ContentTransferEncodingError
        If *encoding* is not recognised, or if the payload is malformed
        for the requested encoding.
    """
    forward, inverse = _resolve(encoding)
    if inverse:
        return _FORWARD_ENCODERS[forward](data)
    return _FORWARD_DECODERS[forward](data)
