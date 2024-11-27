from abc import ABC, abstractmethod
from redisauth.token import TokenInterface

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
