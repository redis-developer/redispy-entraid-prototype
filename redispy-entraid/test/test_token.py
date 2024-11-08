from datetime import datetime

import jwt
import pytest
from redisauth.token import SimpleToken, JWToken


class TestToken:

    def test_simple_token(self):
        token = SimpleToken(
            'value',
            datetime.now().timestamp() + 100,
            datetime.now().timestamp(),
            {"key": "value"}
        )

        assert token.ttl() == pytest.approx(100, 1)
        assert token.is_expired() is False
        assert token.try_get('key') == "value"
        assert token.get_value() == "value"
        assert token.get_expires_at() == pytest.approx(datetime.now().timestamp() + 100, 1)
        assert token.get_received_at() == pytest.approx(datetime.now().timestamp(), 1)

        token = SimpleToken(
            'value',
            -1,
            datetime.now().timestamp(),
            {"key": "value"}
        )

        assert token.ttl() == -1
        assert token.is_expired() is False
        assert token.get_expires_at() == -1

    def test_jwt_token(self):
        token = {
            'exp': datetime.now().timestamp() + 100,
            'iat': datetime.now().timestamp(),
            'key': "value"
        }
        encoded = jwt.encode(token, "secret", algorithm='HS256')
        jwt_token = JWToken(encoded)

        assert jwt_token.ttl() == pytest.approx(100, 1)
        assert jwt_token.is_expired() is False
        assert jwt_token.try_get('key') == "value"
        assert jwt_token.get_value() == encoded
        assert jwt_token.get_expires_at() == pytest.approx(datetime.now().timestamp() + 100, 1)
        assert jwt_token.get_received_at() == pytest.approx(datetime.now().timestamp(), 1)

        token = {
            'exp': -1,
            'iat': datetime.now().timestamp(),
            'key': "value"
        }
        encoded = jwt.encode(token, "secret", algorithm='HS256')
        jwt_token = JWToken(encoded)

        assert jwt_token.ttl() == -1
        assert jwt_token.is_expired() is False
        assert jwt_token.get_expires_at() == -1
