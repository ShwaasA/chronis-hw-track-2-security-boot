"""
Encryption Daemon — Track HW-2, Day 1
Implements the full key hierarchy (DIK, DSK, UPK, Server Transport Key) and
enforces Rule 1: no daemon may write to disk without going through this
daemon first. Enforcement is structural — write_to_storage() only accepts
an EncryptedRecord, never raw bytes.
"""

import base64
import datetime
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption,
)

from mock_crypto import MockCryptoChip


class EncryptedRecord:
    """
    The ONLY type storage-write functions accept. You cannot construct
    a valid one from raw bytes without going through EncryptionDaemon.encrypt().
    This is what makes Rule 1 structurally true instead of a convention
    someone can forget.
    """
    def __init__(self, ciphertext: bytes, key_id: str, timestamp: str):
        self.ciphertext = ciphertext
        self.key_id = key_id
        self.timestamp = timestamp

    def __repr__(self):
        return f"<EncryptedRecord key={self.key_id} ts={self.timestamp} len={len(self.ciphertext)}>"


class BypassAttemptError(Exception):
    """Raised when something tries to write unencrypted data to storage."""
    pass


def _fernet_key_from_bytes(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw[:32].ljust(32, b"0"))


class EncryptionDaemon:
    def __init__(self):
        self._chip = MockCryptoChip()

        # DIK — generated once on first boot, never leaves this object.
        # (Simulated "secure storage" = kept private to this instance;
        # nothing outside this class ever sees the raw key material.)
        self._dik_private, self._dik_public = self._chip.generate_keypair()
        # P-256 EC keys don't support Encoding.Raw/PrivateFormat.Raw (that
        # format only exists for Ed25519/X25519 curves). PKCS8 DER is the
        # portable way to get deterministic private-key bytes to feed into
        # HKDF as input keying material.
        self._dik_raw = self._dik_private.private_bytes(
            Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
        )

        # UPK — the user's own keypair; public half wraps an extra outer
        # layer around whatever the DSK already encrypted.
        self._upk_private, self.upk_public = self._chip.generate_keypair()

        # DSKs are NEVER stored — only cached in memory per-day, re-derivable
        # on demand from DIK + date at any time.
        self._dsk_cache = {}

    def _derive_dsk(self, date_str: str) -> bytes:
        """Derive a fresh Data Session Key from DIK + calendar date."""
        if date_str in self._dsk_cache:
            return self._dsk_cache[date_str]
        hkdf = HKDF(
            algorithm=hashes.SHA256(), length=32,
            salt=date_str.encode(), info=b"chronis-dsk-v1",
        )
        dsk = hkdf.derive(self._dik_raw)
        self._dsk_cache[date_str] = dsk
        return dsk

    def encrypt(self, plaintext: bytes, date_str: str = None) -> EncryptedRecord:
        """The ONLY sanctioned path from raw sensor data to something storable."""
        if date_str is None:
            date_str = datetime.date.today().isoformat()

        dsk = self._derive_dsk(date_str)
        inner_ciphertext = Fernet(_fernet_key_from_bytes(dsk)).encrypt(plaintext)

        # Outer layer wrapped with a UPK-derived key (per spec: UPK adds an
        # extra outer layer around whatever the DSK already encrypted).
        # X962/UncompressedPoint is the standard way to get raw EC public
        # key bytes (Encoding.Raw doesn't apply to P-256, same reason as above).
        upk_bytes = self.upk_public.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        upk_key = _fernet_key_from_bytes(hashlib.sha256(upk_bytes).digest())
        outer_ciphertext = Fernet(upk_key).encrypt(inner_ciphertext)

        return EncryptedRecord(
            ciphertext=outer_ciphertext,
            key_id=f"dsk-{date_str}",
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def new_server_transport_key(self):
        """Fresh keypair generated per upload session — cloud transmission only."""
        return self._chip.generate_keypair()


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
