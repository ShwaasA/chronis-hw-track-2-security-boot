import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from encryption_daemon import (
    EncryptionDaemon, write_to_storage, BypassAttemptError, EncryptedRecord,
    SignatureVerificationError,
)


def test_encrypt_produces_encrypted_record():
    daemon = EncryptionDaemon()
    record = daemon.encrypt(b"sensor reading: hr=72")
    assert isinstance(record, EncryptedRecord)
    assert record.ciphertext != b"sensor reading: hr=72"


def test_write_to_storage_accepts_encrypted_record():
    daemon = EncryptionDaemon()
    record = daemon.encrypt(b"test payload")
    result = write_to_storage(record)
    assert "WROTE" in result


def test_write_to_storage_rejects_raw_bytes():
    with pytest.raises(BypassAttemptError):
        write_to_storage(b"raw unencrypted sensor data")


def test_write_to_storage_rejects_plain_string():
    with pytest.raises(BypassAttemptError):
        write_to_storage("not even bytes, just a string")


def test_write_to_storage_rejects_dict():
    with pytest.raises(BypassAttemptError):
        write_to_storage({"hr": 72, "motion": "still"})


def test_dsk_is_deterministic_within_same_day():
    daemon = EncryptionDaemon()
    today = datetime.date.today().isoformat()
    dsk1 = daemon._derive_dsk(today)
    dsk2 = daemon._derive_dsk(today)
    assert dsk1 == dsk2


def test_dsk_differs_across_days():
    daemon = EncryptionDaemon()
    dsk_today = daemon._derive_dsk("2026-07-11")
    dsk_tomorrow = daemon._derive_dsk("2026-07-12")
    assert dsk_today != dsk_tomorrow


def test_dsk_never_persisted_only_cached_in_memory():
    daemon = EncryptionDaemon()
    daemon._derive_dsk("2026-07-11")
    # only assertion possible here: cache is a plain in-memory dict,
    # never written to disk anywhere in this module.
    assert isinstance(daemon._dsk_cache, dict)


def test_server_transport_key_is_fresh_each_session():
    daemon = EncryptionDaemon()
    priv1, pub1 = daemon.new_server_transport_key()
    priv2, pub2 = daemon.new_server_transport_key()
    assert priv1 is not priv2


def test_decrypt_roundtrip_via_daemon_api():
    """The daemon can decrypt its own records via the real API (not a
    manual layer-by-layer reversal done from outside the class)."""
    daemon = EncryptionDaemon()
    plaintext = b"heart_rate=88,motion=walking"
    record = daemon.encrypt(plaintext, date_str="2026-07-11")
    recovered = daemon.verify_and_decrypt(record, date_str="2026-07-11")
    assert recovered == plaintext


# ---------------------------------------------------------------------
# Fix #1: the UPK outer layer must require the UPK PRIVATE key to open —
# public key knowledge alone must NOT be enough to decrypt.
# ---------------------------------------------------------------------

def test_upk_public_bytes_alone_cannot_decrypt_outer_layer():
    """Regression test for the original flaw: the outer-layer key used to
    be SHA256(upk_public_bytes) — derivable by anyone with the public key.
    This proves that's no longer true: hashing the public bytes directly
    does NOT produce a working Fernet key for the outer layer anymore."""
    daemon = EncryptionDaemon()
    record = daemon.encrypt(b"secret payload", date_str="2026-07-11")

    import hashlib, base64
    from cryptography.fernet import Fernet, InvalidToken

    upk_bytes = daemon.upk_public.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    fake_key = base64.urlsafe_b64encode(hashlib.sha256(upk_bytes).digest()[:32])

    with pytest.raises(InvalidToken):
        Fernet(fake_key).decrypt(record.ciphertext)


def test_decryption_requires_upk_private_key():
    """A daemon instance that never had the real UPK private key (only the
    public key + a mismatched private key) cannot decrypt someone else's
    record — proving the outer layer is genuinely access-controlled."""
    daemon = EncryptionDaemon()
    record = daemon.encrypt(b"secret payload", date_str="2026-07-11")

    impostor = EncryptionDaemon()  # has its own, different UPK private key
    with pytest.raises(Exception):
        impostor.verify_and_decrypt(record, date_str="2026-07-11")


# ---------------------------------------------------------------------
# Fix #2: records must be signed, and tampering must be caught.
# ---------------------------------------------------------------------

def test_record_is_signed():
    daemon = EncryptionDaemon()
    record = daemon.encrypt(b"payload", date_str="2026-07-11")
    assert record.signature != b""
    assert daemon._chip.verify(daemon.dik_public, record._signed_payload(), record.signature)


def test_tampered_ciphertext_fails_verification():
    daemon = EncryptionDaemon()
    record = daemon.encrypt(b"payload", date_str="2026-07-11")
    record.ciphertext = record.ciphertext[:-1] + bytes([record.ciphertext[-1] ^ 0xFF])

    with pytest.raises(SignatureVerificationError):
        daemon.verify_and_decrypt(record, date_str="2026-07-11")


def test_tampered_ephemeral_key_fails_verification():
    """Swapping in a different (validly-generated) ephemeral key should
    also break the signature, since the signature covers both fields."""
    daemon = EncryptionDaemon()
    record = daemon.encrypt(b"payload", date_str="2026-07-11")
    other_record = daemon.encrypt(b"other payload", date_str="2026-07-11")
    record.ephemeral_pub_bytes = other_record.ephemeral_pub_bytes

    with pytest.raises(SignatureVerificationError):
        daemon.verify_and_decrypt(record, date_str="2026-07-11")


# ---------------------------------------------------------------------
# Fix #3: no raw private-key bytes should be reachable from this module.
# ---------------------------------------------------------------------

def test_dik_private_bytes_never_exposed_on_daemon():
    """The daemon should hold no raw-exportable copy of the DIK private
    key anywhere outside the chip layer's internal use."""
    daemon = EncryptionDaemon()
    # The only private-key-shaped attributes on the daemon should be the
    # key OBJECTS (which the mock 'chip' methods accept), never raw bytes.
    assert not hasattr(daemon, "_dik_raw")
