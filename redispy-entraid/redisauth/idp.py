from abc import ABC, abstractmethod

'''
This interface is the facade of an identity provider
'''


class IdentityProviderConfigInterface(ABC):
    @abstractmethod
    def get_credentials(self) -> dict:
        pass


class IdentityProviderInterface(ABC):
    """
    Receive a token from the identity provider. Receiving a token only works when being authenticated.
    """

    @abstractmethod
    def request_token(self):
        pass

    @abstractmethod
    def get_config(self) -> IdentityProviderConfigInterface:
        pass
