"""
Encryption Daemon — Track HW-2, Day 1
Implements the full key hierarchy (DIK, DSK, UPK, Server Transport Key) and
enforces Rule 1: no daemon may write to disk without going through this
daemon first. Enforcement is structural — write_to_storage() only accepts
an EncryptedRecord, never raw bytes.

FIXES vs. the previous version:

1. UPK outer layer now actually requires the UPK private key to open.
   The old version derived the outer-layer key as SHA256(UPK_PUBLIC_bytes)
   — since UPK is meant to be non-secret, anyone with the public key alone
   could decrypt the outer layer, which defeated the point of a
   "public-key-wrapped" layer entirely. This version does real ECIES:
   a fresh ephemeral keypair is generated per record, ECDH'd against the
   UPK public key to get a shared secret, and that shared secret (not the
   public key bytes) becomes the wrap key. Only whoever holds the UPK
   *private* key can redo that ECDH and recover the shared secret.

2. Records are now signed, and can be verified.
   MockCryptoChip.sign()/verify() existed but were never called. Every
   EncryptedRecord is now signed with the DIK private key, and
   EncryptionDaemon.verify_and_decrypt() checks that signature before
   decrypting anything. This is what actually gives the "signing" the
   crypto chip is for.

3. No raw private-key bytes leave the chip layer.
   DSK derivation used to pull `dik_private.private_bytes(...)` directly
   into this file and feed it to HKDF here. That can't happen on a real
   ATECC608B configured with the private-key slot set "No Read." DSK
   derivation is now delegated to MockCryptoChip.derive_key(), which
   keeps that key-touching code inside the one file (mock_crypto.py)
   that's meant to model chip-internal behavior.
"""

import base64
import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from mock_crypto import MockCryptoChip


class EncryptedRecord:
    """
    The ONLY type storage-write functions accept. You cannot construct
    a valid one from raw bytes without going through EncryptionDaemon.encrypt().
    This is what makes Rule 1 structurally true instead of a convention
    someone can forget.

    ephemeral_pub_bytes: the one-time public key used for this record's
      ECIES wrap. Needed by whoever holds the UPK private key to redo the
      ECDH and recover the shared secret — not secret itself.
    signature: DIK signature over (ciphertext + ephemeral_pub_bytes),
      proving this record came from this device and hasn't been altered.
    """
    def __init__(self, ciphertext: bytes, key_id: str, timestamp: str,
                 ephemeral_pub_bytes: bytes, signature: bytes):
        self.ciphertext = ciphertext
        self.key_id = key_id
        self.timestamp = timestamp
        self.ephemeral_pub_bytes = ephemeral_pub_bytes
        self.signature = signature

    def _signed_payload(self) -> bytes:
        """The exact bytes the signature covers — ciphertext bound to the
        ephemeral key used for that ciphertext, so neither can be swapped
        independently without invalidating the signature."""
        return self.ephemeral_pub_bytes + self.ciphertext

    def __repr__(self):
        return (f"<EncryptedRecord key={self.key_id} ts={self.timestamp} "
                f"len={len(self.ciphertext)}>")


class BypassAttemptError(Exception):
    """Raised when something tries to write unencrypted data to storage."""
    pass


class SignatureVerificationError(Exception):
    """Raised when a record's signature doesn't match — tampering or
    corruption. Never decrypt a record that fails this check."""
    pass


def _fernet_key_from_bytes(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw[:32].ljust(32, b"0"))


class EncryptionDaemon:
    def __init__(self):
        self._chip = MockCryptoChip()

        # DIK — generated once on first boot. Private half never leaves
        # this object, and is only ever passed *into* chip.sign()/
        # chip.derive_key() — never read out as raw bytes here.
        self._dik_private, self.dik_public = self._chip.generate_keypair()

        # UPK — the user's own keypair; public half wraps an extra outer
        # layer around whatever the DSK already encrypted. Private half
        # belongs to the user, not the device — this daemon holds it only
        # because it's simulating both sides for the Day 1 mock. In the
        # real system the device only ever sees upk_public.
        self._upk_private, self.upk_public = self._chip.generate_keypair()

        # DSKs are NEVER stored — only cached in memory per-day,
        # re-derivable on demand from DIK + date at any time.
        self._dsk_cache = {}

    def _derive_dsk(self, date_str: str) -> bytes:
        """Derive a fresh Data Session Key from DIK + calendar date, via
        the chip's on-chip KDF — the DIK private key itself never leaves
        the chip layer to do this."""
        if date_str in self._dsk_cache:
            return self._dsk_cache[date_str]
        dsk = self._chip.derive_key(
            self._dik_private,
            salt=date_str.encode(),
            info=b"chronis-dsk-v1",
            length=32,
        )
        self._dsk_cache[date_str] = dsk
        return dsk

    def encrypt(self, plaintext: bytes, date_str: str = None) -> EncryptedRecord:
        """The ONLY sanctioned path from raw sensor data to something storable."""
        if date_str is None:
            date_str = datetime.date.today().isoformat()

        # Inner layer: DSK-encrypted.
        dsk = self._derive_dsk(date_str)
        inner_ciphertext = Fernet(_fernet_key_from_bytes(dsk)).encrypt(plaintext)

        # Outer layer: real ECIES against UPK, not a hash of the public key.
        # Fresh ephemeral keypair per record so a compromised ephemeral key
        # only ever exposes that one record.
        ephemeral_private, ephemeral_public = self._chip.generate_keypair()
        shared_secret = self._chip.ecdh(ephemeral_private, self.upk_public)
        # HKDF-stretch the shared secret (not a private key — the output of
        # an already-completed ECDH) into a usable symmetric key.
        wrap_key = _fernet_key_from_bytes(
            _hkdf_stretch(shared_secret, salt=b"chronis-upk-wrap-v1", info=b"chronis-upk-wrap-v1")
        )
        outer_ciphertext = Fernet(wrap_key).encrypt(inner_ciphertext)

        ephemeral_pub_bytes = ephemeral_public.public_bytes(
            Encoding.X962, PublicFormat.UncompressedPoint
        )

        record = EncryptedRecord(
            ciphertext=outer_ciphertext,
            key_id=f"dsk-{date_str}",
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ephemeral_pub_bytes=ephemeral_pub_bytes,
            signature=b"",  # filled in below
        )
        record.signature = self._chip.sign(self._dik_private, record._signed_payload())
        return record

    def verify_and_decrypt(self, record: EncryptedRecord, date_str: str) -> bytes:
        """
        The counterpart to encrypt(): verify the DIK signature, then peel
        both layers using the UPK private key + DSK. Raises
        SignatureVerificationError if the record was tampered with or
        didn't come from this device's DIK — decryption is never attempted
        on a record that fails verification.
        """
        if not self._chip.verify(self.dik_public, record._signed_payload(), record.signature):
            raise SignatureVerificationError(
                f"signature check failed for record {record.key_id} — "
                "refusing to decrypt a record that may have been tampered with"
            )

        from cryptography.hazmat.primitives.asymmetric import ec
        ephemeral_public = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), record.ephemeral_pub_bytes
        )
        shared_secret = self._chip.ecdh(self._upk_private, ephemeral_public)
        wrap_key = _fernet_key_from_bytes(
            _hkdf_stretch(shared_secret, salt=b"chronis-upk-wrap-v1", info=b"chronis-upk-wrap-v1")
        )
        inner_ciphertext = Fernet(wrap_key).decrypt(record.ciphertext)

        dsk = self._derive_dsk(date_str)
        return Fernet(_fernet_key_from_bytes(dsk)).decrypt(inner_ciphertext)

    def new_server_transport_key(self):
        """Fresh keypair generated per upload session — cloud transmission only."""
        return self._chip.generate_keypair()


def _hkdf_stretch(shared_secret: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF over an already-computed ECDH shared secret. This is a plain
    key-derivation step over public *output* (the shared secret), not a
    private-key export — HKDF is the standard way to turn a raw ECDH
    shared secret into a usable symmetric key (RFC 5869 / SEC1 §3.6)."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info)
    return hkdf.derive(shared_secret)


def write_to_storage(record) -> str:
    """
    THE ONLY function in the system allowed to touch disk.
    Rule 1, enforced structurally: pass anything other than an
    EncryptedRecord and this raises immediately.
    """
    if not isinstance(record, EncryptedRecord):
        raise BypassAttemptError(
            "write_to_storage() requires an EncryptedRecord — raw bytes are "
            "rejected. Route data through EncryptionDaemon.encrypt() first."
        )
    return f"WROTE key={record.key_id} ts={record.timestamp} bytes={len(record.ciphertext)}"
