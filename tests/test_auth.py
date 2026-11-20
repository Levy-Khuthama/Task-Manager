import pytest

from taskmanager.auth import hash_password, verify_password


def test_correct_password_verifies():
    assert verify_password("s3cret-pass", hash_password("s3cret-pass"))


def test_wrong_password_is_rejected():
    assert not verify_password("wrong", hash_password("s3cret-pass"))


def test_hash_does_not_contain_the_plaintext():
    assert "s3cret-pass" not in hash_password("s3cret-pass")


def test_same_password_gets_a_different_hash_each_time():
    assert hash_password("same") != hash_password("same")


def test_fixed_salt_gives_a_repeatable_hash():
    first = hash_password("same", salt=b"0123456789abcdef", iterations=1_000)
    second = hash_password("same", salt=b"0123456789abcdef", iterations=1_000)
    assert first == second


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "plain-text-password",
        "md5$1$aa$bb",
        "pbkdf2_sha256$not-a-number$00$00",
        "pbkdf2_sha256$1000$zz$yy",
        "pbkdf2_sha256$0$00$00",
    ],
)
def test_malformed_stored_values_fail_instead_of_raising(stored):
    assert verify_password("anything", stored) is False
