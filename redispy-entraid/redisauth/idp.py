from abc import ABC, abstractmethod

import jwt
from datetime import datetime, timedelta
from redisauth.token import SimpleToken, JWToken
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
