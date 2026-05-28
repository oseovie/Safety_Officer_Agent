from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("S@ferPass123")
    assert verify_password("S@ferPass123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_access_token("user-1", "tenant-1", "owner")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-1"
