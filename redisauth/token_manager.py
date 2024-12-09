import threading
import weakref
from datetime import datetime, timezone
from typing import Callable, Any, Awaitable, Coroutine, Union

import asyncio

from redisauth.err import RequestTokenErr, TokenRenewalErr
from redisauth.idp import IdentityProviderInterface
from redisauth.token import TokenResponse
import logging

logger = logging.getLogger(__name__)


class CredentialsListener:
    """
    Listeners that will be notified on events related to credentials.
    Accepts callbacks and awaitable callbacks.
    """
    def __init__(self):
        self._on_next = None
        self._on_error = None

    @property
    def on_next(self) -> Union[weakref.WeakMethod[Callable[[Any], None]], Awaitable]:
        return self._on_next

    @on_next.setter
    def on_next(self, callback: Union[Callable[[Any], None], Awaitable]) -> None:
        self._on_next = weakref.WeakMethod(callback)

    @property
    def on_error(self) -> Union[weakref.WeakMethod[Callable[[Exception], None]], Awaitable]:
        return self._on_error

    @on_error.setter
    def on_error(self, callback: Union[Callable[[Exception], None], Awaitable]) -> None:
        self._on_error = weakref.WeakMethod(callback)


class RetryPolicy:
    def __init__(self, max_attempts: int, delay_in_ms: float):
        self.max_attempts = max_attempts
        self.delay_in_ms = delay_in_ms

    def get_max_attempts(self) -> int:
        """
        Retry attempts before exception will be thrown.

        :return: int
        """
        return self.max_attempts

    def get_delay_in_ms(self) -> float:
        """
        Delay between retries in seconds.

        :return: int
        """
        return self.delay_in_ms


class TokenManagerConfig:
    def __init__(
            self,
            expiration_refresh_ratio: float,
            lower_refresh_bound_millis: int,
            token_request_execution_timeout_in_ms: int,
            retry_policy: RetryPolicy,
    ):
        self._expiration_refresh_ratio = expiration_refresh_ratio
        self._lower_refresh_bound_millis = lower_refresh_bound_millis
        self._token_request_execution_timeout_in_ms = token_request_execution_timeout_in_ms
        self._retry_policy = retry_policy

    def get_expiration_refresh_ratio(self) -> float:
        """
        Represents the ratio of a token's lifetime at which a refresh should be triggered.
        For example, a value of 0.75 means the token should be refreshed when 75% of its
        lifetime has elapsed (or when 25% of its lifetime remains).

        :return: float
        """

        return self._expiration_refresh_ratio

    def get_lower_refresh_bound_millis(self) -> int:
        """
        Represents the minimum time in milliseconds before token expiration to trigger a refresh, in milliseconds.
        This value sets a fixed lower bound for when a token refresh should occur, regardless
        of the token's total lifetime.
        If set to 0 there will be no lower bound and the refresh will be triggered
        based on the expirationRefreshRatio only.

        :return: int
        """
        return self._lower_refresh_bound_millis

    def get_token_request_execution_timeout_in_ms(self) -> int:
        """
        Represents the maximum time in milliseconds to wait for a token request to complete.

        :return: int
        """
        return self._token_request_execution_timeout_in_ms

    def get_retry_policy(self) -> RetryPolicy:
        """
        Represents the retry policy for token requests.

        :return: RetryPolicy
        """
        return self._retry_policy


class TokenManager:
    def __init__(self, identity_provider: IdentityProviderInterface, config: TokenManagerConfig):
        self._idp = identity_provider
        self._config = config
        self._next_timer = None
        self._stop_event = threading.Event()
        self._listener = None
        self._init_timer = None
        self._retries = 0

    def __del__(self):
        self.stop()

    def start(
            self,
            listener: CredentialsListener,
            block_for_initial: bool = False,
            initial_delay_in_ms: float = 0,
    ) -> Callable[[], None]:
        self._listener = listener

        # Schedule initial task, that will run subsequent tasks with interval.
        # Weakref is used to make sure that GC can stop child thread correctly.
        self._init_timer = threading.Timer(
            initial_delay_in_ms / 1000,
            _renew_token,
            args=(weakref.ref(self),)
        )
        self._init_timer.daemon = True
        self._init_timer.start()

        if block_for_initial:
            self._init_timer.join()

        return self.stop

    def stop(self):
        self._stop_event.set()

        if self._next_timer is not None:
            self._next_timer.cancel()

    def acquire_token(self, force_refresh=False) -> TokenResponse:
        return TokenResponse(self._idp.request_token(force_refresh))

    def _calculate_renewal_delay(self, expire_date: float) -> float:
        delay_for_lower_refresh = self._delay_for_lower_refresh(expire_date)
        delay_for_ratio_refresh = self._delay_for_ratio_refresh(expire_date)
        delay = min(delay_for_ratio_refresh, delay_for_lower_refresh)

        return 0 if delay < 0 else delay / 1000

    def _delay_for_lower_refresh(self, expire_date: float):
        return (expire_date - self._config.get_lower_refresh_bound_millis() -
                (datetime.now(timezone.utc).timestamp() * 1000))

    def _delay_for_ratio_refresh(self, expire_date: float):
        token_ttl = expire_date - (datetime.now(timezone.utc).timestamp() * 1000)
        refresh_before = token_ttl - (token_ttl * self._config.get_expiration_refresh_ratio())

        return expire_date - refresh_before - (datetime.now(timezone.utc).timestamp() * 1000)


# To make sure that GC isn't blocked by strong references to TokenManager object,
# we have to use weakref, so we can stop execution whenever main thread is finished.
def _renew_token(mgr_ref: weakref.ref[TokenManager]):
    """
    Task to renew token from identity provider.
    Schedules renewal tasks based on token TTL.

    :param mgr_ref:
    :return:
    """
    mgr = mgr_ref()

    if mgr._stop_event.is_set():
        return None

    try:
        token_res = mgr.acquire_token(force_refresh=True)
        delay = mgr._calculate_renewal_delay(
            token_res.get_token().get_expires_at_ms(),
        )

        if token_res.get_token().is_expired():
            raise TokenRenewalErr("Requested token is expired")

        # If reference was already cleared by GC, return current token.
        if mgr._listener.on_next is None or mgr._listener.on_next() is None:
            return token_res

        try:
            mgr._listener.on_next()(token_res.get_token())
        except Exception as e:
            raise TokenRenewalErr(e)

        if delay <= 0:
            return token_res

        mgr._next_timer = threading.Timer(
            delay,
            _renew_token,
            args=(mgr_ref,)
        )
        mgr._next_timer.daemon = True
        mgr._next_timer.start()
        return token_res
    except RequestTokenErr as e:
        if mgr._retries < mgr._config.get_retry_policy().get_max_attempts():
            mgr._retries += 1
            mgr._next_timer = threading.Timer(
                mgr._config.get_retry_policy().get_delay_in_ms() / 1000,
                _renew_token,
                args=(mgr_ref,)
            )
            mgr._next_timer.daemon = True
            mgr._next_timer.start()
        else:
            if mgr._listener.on_error is None or mgr._listener.on_error() is None:
                raise e
            mgr._listener.on_error()(e)
    except TokenRenewalErr as e:
        if mgr._listener.on_error is None or mgr._listener.on_error() is None:
            raise e

        mgr._listener.on_error()(e)