"""
Mock Crypto Interface — Track HW-2, Day 1
TEMPORARY STAND-IN for the real ATECC608B security chip API surface.
Matches the function shape the real chip driver will eventually expose:
generate_keypair(), sign(), verify(). Uses real software crypto
(the `cryptography` library) underneath, so behavior is cryptographically
correct — only the "chip" part is fake. Delete this file and swap in the
real chip driver once hardware arrives; nothing above this layer changes.

CURVE CHOICE: NIST P-256 (secp256r1) with ECDSA — this is deliberate, not
arbitrary. The ATECC608B only supports P-256 for ECDSA sign/verify, not
Ed25519. If this mock used Ed25519 instead, "swap the mock for the real
chip" would actually mean "rewrite the signing logic," which defeats the
entire point of building against a mock. Matching the real chip's
actual algorithm now is what makes the later swap a one-line change.
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature


class MockCryptoChip:
    """Stand-in for ATECC608B. Real driver will wrap actual chip I2C calls."""

    def generate_keypair(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        return private_key, public_key

    def sign(self, private_key, data: bytes) -> bytes:
        return private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    def verify(self, public_key, data: bytes, signature: bytes) -> bool:
        try:
            public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
