from typing import Union, Tuple

from redis import CredentialProvider
from redisauth.token_manager import TokenManager, CredentialsListener


class EntraIdCredentialsProvider(CredentialProvider):
    def __init__(self, token_mgr: TokenManager):
        self._token_mgr = token_mgr
        self._listener = None
        self._is_listening = False

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        if self._listener is None:
            raise Exception('To obtain the credentials the listener must be set first')

        init_token = self._token_mgr.acquire_token()

        if self._is_listening is False:
            self._token_mgr.start(
                self._listener
            )
            self._is_listening = True

        return (init_token.get_token().get_value(),)

    def set_listener(self, listener: CredentialsListener):
        self._listener = listener

    def is_listening(self) -> bool:
        return self._is_listening












