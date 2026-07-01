from app.security import create_session_token, hash_password, read_session_token, verify_password


def test_hash_and_verify_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_hash_is_not_plaintext():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert hashed.startswith("$2b$")


def test_session_token_roundtrip():
    token = create_session_token("sebastian")
    assert read_session_token(token) == "sebastian"


def test_session_token_rejects_tampering():
    # Ein Zeichen in der Mitte kippen statt am Ende - das letzte Base64-Zeichen
    # eines Segments kann "Don't-care"-Padding-Bits haben, die die dekodierten
    # Bytes nicht verändern und den Test unzuverlässig machen würden.
    token = create_session_token("sebastian")
    mid = len(token) // 2
    tampered = token[:mid] + ("a" if token[mid] != "a" else "b") + token[mid + 1:]
    assert read_session_token(tampered) is None


def test_session_token_rejects_garbage():
    assert read_session_token("not-a-real-token") is None
