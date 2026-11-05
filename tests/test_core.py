"""Tests for mini_mime_content_transfer.

Run with::

    PYTHONPATH=src python -m unittest discover -s tests
"""

import unittest

from mini_mime_content_transfer import (
    ContentTransferEncodingError,
    ENCODINGS,
    decode,
    encode,
)


class IdentityEncodingTests(unittest.TestCase):
    def test_7bit_round_trip(self) -> None:
        payload = b"hello world"
        self.assertEqual(encode(payload, "7bit"), payload)
        self.assertEqual(decode(payload, "7bit"), payload)

    def test_8bit_round_trip(self) -> None:
        payload = bytes(range(256))
        self.assertEqual(encode(payload, "8bit"), payload)
        self.assertEqual(decode(payload, "8bit"), payload)

    def test_binary_round_trip(self) -> None:
        payload = b"\x00\x01\x02\xff\xfe"
        self.assertEqual(encode(payload, "binary"), payload)
        self.assertEqual(decode(payload, "binary"), payload)


class Base64Tests(unittest.TestCase):
    def test_encode_known_value(self) -> None:
        self.assertEqual(encode(b"any carnal pleasure.", "base64"), b"YW55IGNhcm5hbCBwbGVhc3VyZS4=")

    def test_encode_wraps_at_76_characters(self) -> None:
        payload = b"A" * 100
        encoded = encode(payload, "base64")
        lines = encoded.split(b"\r\n")
        self.assertTrue(all(len(line) <= 76 for line in lines))
        self.assertEqual(decode(encoded, "base64"), payload)

    def test_decode_ignores_whitespace(self) -> None:
        self.assertEqual(decode(b"YW55IGNh\r\ncm5hbCBwbGVhc3VyZS4=", "base64"), b"any carnal pleasure.")

    def test_decode_rejects_invalid_characters(self) -> None:
        with self.assertRaises(ContentTransferEncodingError):
            decode(b"!!!!", "base64")

    def test_inverse_swaps_direction(self) -> None:
        raw = b"any carnal pleasure."
        encoded = encode(raw, "base64")
        self.assertEqual(encode(encoded, "base64-inverse"), raw)
        self.assertEqual(decode(raw, "base64-inverse"), encoded)


class QuotedPrintableTests(unittest.TestCase):
    def test_encode_known_value(self) -> None:
        self.assertEqual(encode(b"=3D", "quoted-printable"), b"=3D3D")

    def test_round_trip_with_binary(self) -> None:
        payload = bytes(range(256))
        encoded = encode(payload, "quoted-printable")
        self.assertEqual(decode(encoded, "quoted-printable"), payload)

    def test_inverse_swaps_direction(self) -> None:
        raw = b"hello=world"
        encoded = encode(raw, "quoted-printable")
        self.assertEqual(encode(encoded, "quoted-printable-inverse"), raw)
        self.assertEqual(decode(raw, "quoted-printable-inverse"), encoded)


class ErrorHandlingTests(unittest.TestCase):
    def test_unknown_encoding_raises(self) -> None:
        with self.assertRaises(ContentTransferEncodingError):
            encode(b"x", "rot13")
        with self.assertRaises(ContentTransferEncodingError):
            decode(b"x", "rot13")

    def test_unknown_inverse_encoding_raises(self) -> None:
        with self.assertRaises(ContentTransferEncodingError):
            encode(b"x", "rot13-inverse")

    def test_encodings_constant_lists_all_seven(self) -> None:
        self.assertEqual(len(ENCODINGS), 7)
        self.assertIn("7bit", ENCODINGS)
        self.assertIn("8bit", ENCODINGS)
        self.assertIn("binary", ENCODINGS)
        self.assertIn("base64", ENCODINGS)
        self.assertIn("quoted-printable", ENCODINGS)
        self.assertIn("base64-inverse", ENCODINGS)
        self.assertIn("quoted-printable-inverse", ENCODINGS)


if __name__ == "__main__":
    unittest.main()
