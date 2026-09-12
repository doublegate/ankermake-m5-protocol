from libflagship.megajank import (
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    crypto_curse_string,
    crypto_decurse_string,
    mqtt_checksum_add,
    mqtt_checksum_remove,
    simple_decrypt_string,
    simple_encrypt_string,
    xor_bytes,
)
from libflagship.seccode import (
    cal_hw_id_suffix,
    calc_check_code,
    create_check_code_v1,
    gen_base_code,
    gen_check_code_v1,
)


def test_aes_encrypt_decrypt_round_trip():
    key = b"0123456789abcdef"
    iv = b"abcdefghijklmnop"
    msg = b"secret payload"

    encrypted = aes_cbc_encrypt(msg, key, iv)

    assert encrypted != msg
    assert aes_cbc_decrypt(encrypted, key, iv) == msg


def test_mqtt_checksum_helpers_round_trip():
    payload = b"hello mqtt"
    checksummed = mqtt_checksum_add(payload)

    assert xor_bytes(checksummed) == 0
    assert mqtt_checksum_remove(checksummed) == payload


def test_pppp_crypto_round_trips():
    assert crypto_decurse_string(crypto_curse_string(b"hello")) == b"hello"
    assert simple_decrypt_string(simple_encrypt_string(b"hello")) == b"hello"


def test_seccode_reference_values(monkeypatch):
    sn = b"ABCD1234"
    mac = b"a1b2c3d4e5f6"

    assert calc_check_code("ABCD1234", "a1b2c3d4e5f6") == "d03147d88c2741e9320b0657fbed1063"
    assert cal_hw_id_suffix(mac) == 40
    assert gen_base_code(sn, mac) == b"123440"
    assert gen_check_code_v1(b"123440", b"ABCDEF1234567890ABCDEF1234567890") == "8611D0D6BC18E76CB3AEEC319ED1149B"

    monkeypatch.setattr("libflagship.seccode.secrets.randbelow", lambda n: 12345678)
    assert create_check_code_v1(sn, mac) == ("0122345678", "60D81273A8CDEB7E4D4539BC5C8AF398")
