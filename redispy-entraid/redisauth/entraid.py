from typing import Union, Tuple, Callable, Any

from redis.credentials import StreamingCredentialProvider
from redisauth.token_manager import TokenManager, CredentialsListener


class EntraIdCredentialsProvider(StreamingCredentialProvider):
    def __init__(self, token_mgr: TokenManager):
        self._token_mgr = token_mgr
        self._listener = None
        self._is_streaming = False

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        if self._listener is None:
            raise Exception('To obtain the credentials the listener must be set first')

        init_token = self._token_mgr.acquire_token()

        if self._is_streaming is False:
            self._token_mgr.start(
                self._listener
            )
            self._is_streaming = True

        return (init_token.get_token().get_value(),)

    def on_next(self, callback: Callable[[Any], None]):
        self._listener = CredentialsListener()
        self._listener.on_next(callback)

    def is_streaming(self) -> bool:
        return self._is_streaming












