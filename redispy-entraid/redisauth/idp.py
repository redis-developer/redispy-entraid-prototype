from abc import ABC, abstractmethod

import jwt
from datetime import datetime, timedelta
from redisauth.token import Token, JWToken
from redisauth.err import ErrNotAuthenticated

'''
This interface is the facade of an identity provider
'''


class IdentityProviderInterface(ABC):
    """
    Receive a token from the identity provider. Receiving a token only works when being authenticated.
    """

    @abstractmethod
    def request_token(self):
        pass


class IdentityProviderConfigInterface(ABC):
    @abstractmethod
    def get_provider(self) -> IdentityProviderInterface:
        pass


'''
A very simple fake identity provider for testing purposes
'''


class FakeIdentityProvider(IdentityProviderInterface):
    SIGN = "secret"

    '''
    Initialize by authenticating
    '''

    def __init__(self, user, password):
        self.creds = {'user': user, 'password': password}
        self.is_authenticated = False

        if self.creds['user'] == "testuser" and self.creds['password'] == "password":
            self.is_authenticated = True

    def request_token(self) -> Token:
        if self.is_authenticated:
            payload = {
                "user_id": 123,
                "username": "testuser",
                "exp": datetime.utcnow() + timedelta(seconds=10)
            }

            value = jwt.encode(payload, self.SIGN, "HS256")

            return JWToken(value)
        else:
            raise ErrNotAuthenticated()
