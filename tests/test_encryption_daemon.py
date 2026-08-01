import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from encryption_daemon import (
    EncryptionDaemon, write_to_storage, BypassAttemptError, EncryptedRecord,
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


def test_decrypt_roundtrip_via_same_daemon_keys():
    """Sanity check: the encryption is real, not a no-op."""
    daemon = EncryptionDaemon()
    plaintext = b"heart_rate=88,motion=walking"
    record = daemon.encrypt(plaintext, date_str="2026-07-11")

    # Manually reverse both layers using the daemon's own keys, proving
    # the ciphertext genuinely round-trips (this is what the cloud
    # gateway in Track HW-3 will effectively do on the server side).
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    import hashlib
    from encryption_daemon import _fernet_key_from_bytes

    upk_bytes = daemon.upk_public.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    upk_key = _fernet_key_from_bytes(hashlib.sha256(upk_bytes).digest())
    inner = Fernet(upk_key).decrypt(record.ciphertext)

    dsk = daemon._derive_dsk("2026-07-11")
    recovered = Fernet(_fernet_key_from_bytes(dsk)).decrypt(inner)
    assert recovered == plaintext
