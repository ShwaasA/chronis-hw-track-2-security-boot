"""
Mock Crypto Interface — Track HW-2, Day 1
TEMPORARY STAND-IN for the real ATECC608B security chip API surface.
Matches the function shape the real chip driver will eventually expose:
generate_keypair(), sign(), verify(), ecdh(), derive_key(). Uses real
software crypto (the `cryptography` library) underneath, so behavior is
cryptographically correct — only the "chip" part is fake. Delete this
file and swap in the real chip driver once hardware arrives; nothing
above this layer changes.

CURVE CHOICE: NIST P-256 (secp256r1) with ECDSA/ECDH — this is deliberate,
not arbitrary. The ATECC608B only supports P-256 for ECDSA sign/verify and
ECDH, not Ed25519/X25519. Matching the real chip's actual algorithm now is
what makes the later hardware swap a one-line change instead of a rewrite.

KEY-EXPORT DISCIPLINE: every method that touches a private key takes the
private key object in and returns only a *result* (signature, shared
secret, derived key) — never the raw private key bytes. This mirrors how
the real ATECC608B works when a slot is configured "No Read": the chip
will sign, do ECDH, or run its internal KDF using a key, but will never
let the private key material leave the chip. Callers of this mock must
follow the same discipline — if you ever find yourself calling
`private_key.private_bytes(...)` outside this file, that's not something
the real chip can do.
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
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

    def ecdh(self, private_key, peer_public_key) -> bytes:
        """
        On-chip ECDH: combine our private key with someone else's public
        key to get a shared secret. Matches the real ATECC608B's ECDH
        command — the private key never leaves the chip to compute this,
        only the resulting shared secret comes out.
        """
        return private_key.exchange(ec.ECDH(), peer_public_key)

    def derive_key(self, private_key, salt: bytes, info: bytes, length: int = 32) -> bytes:
        """
        On-chip KDF: derive a symmetric key from a private key's material
        without ever exposing that private key material to the caller.
        Models the ATECC608B's internal KDF/HMAC command, which can mix a
        stored private key into a derivation without reading it out.

        Implementation note: this mock still has to touch
        `private_bytes()` *inside this method* to get something to feed
        HKDF — that's unavoidable in a software stand-in. The discipline
        this method exists to enforce is that nothing outside this file
        (i.e. encryption_daemon.py) ever sees those raw bytes; it only
        ever gets the already-derived key back.
        """
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PrivateFormat, NoEncryption,
        )
        raw = private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
        hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info)
        return hkdf.derive(raw)
