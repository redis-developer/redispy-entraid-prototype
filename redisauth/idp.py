from abc import ABC, abstractmethod

from msal import ConfidentialClientApplication
from redisauth.token import TokenInterface, JWToken

'''
This interface is the facade of an identity provider
'''


class IdentityProviderInterface(ABC):
    """
    Receive a token from the identity provider. Receiving a token only works when being authenticated.
    """

    @abstractmethod
    def request_token(self) -> TokenInterface:
        pass


class EntraIDIdentityProvider(IdentityProviderInterface):
    def __init__(self, scopes : list = [], **kwargs):
        self._app = ConfidentialClientApplication(**kwargs)
        self._scopes = scopes

    def request_token(self) -> TokenInterface:
        return JWToken(
            self._app.acquire_token_for_client(self._scopes)["access_token"]
        )
