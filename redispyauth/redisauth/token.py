from abc import ABC, abstractmethod

import jwt
from datetime import datetime, timezone


class TokenInterface(ABC):
    @abstractmethod
    def is_expired(self) -> bool:
        pass

    @abstractmethod
    def ttl(self) -> float:
        pass

    @abstractmethod
    def try_get(self, key: str) -> str:
        pass

    @abstractmethod
    def get_value(self) -> str:
        pass

    @abstractmethod
    def get_expires_at(self) -> int:
        pass

    @abstractmethod
    def get_received_at(self) -> int:
        pass


class TokenResponse:
    def __init__(self, token: TokenInterface):
        self._token = token

    def get_token(self) -> TokenInterface:
        return self._token

    def get_ttl_ms(self) -> int:
        return self._token.get_expires_at() - self._token.get_received_at()


class SimpleToken(TokenInterface):
    def __init__(self, value: str, expires_at: int, received_at: int, claims: dict[str, str]) -> None:
        self.value = value
        self.expires_at = expires_at
        self.received_at = received_at
        self.claims = claims

    def ttl(self) -> float:
        if self.expires_at == -1:
            return -1

        return self.expires_at - datetime.now(timezone.utc).timestamp()

    def is_expired(self) -> bool:
        if self.expires_at == -1:
            return False

        return self.ttl() <= 0

    def try_get(self, key: str) -> str:
        return self.claims.get(key)

    def get_value(self) -> str:
        return self.value

    def get_expires_at(self) -> int:
        return self.expires_at

    def get_received_at(self) -> int:
        return self.received_at


class JWToken(TokenInterface):
    def __init__(self, token: str):
        self._value = token
        self._decoded = jwt.decode(
            self._value,
            options={"verify_signature": False},
            algorithms=[jwt.get_unverified_header(self._value).get('alg')]
        )

    def is_expired(self) -> bool:
        exp = self._decoded['exp']
        if exp == -1:
            return False

        return self._decoded['exp'] <= datetime.now(timezone.utc).timestamp()

    def ttl(self) -> float:
        exp = self._decoded['exp']
        if exp == -1:
            return -1

        return self._decoded['exp'] - datetime.now(timezone.utc).timestamp()

    def try_get(self, key: str) -> str:
        return self._decoded.get(key)

    def get_value(self) -> str:
        return self._value

    def get_expires_at(self) -> int:
        return self._decoded['exp']

    def get_received_at(self) -> int:
        return self._decoded['iat']
