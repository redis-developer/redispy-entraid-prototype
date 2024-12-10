import threading
import weakref
from datetime import datetime, timezone
from time import sleep
from typing import Callable, Any, Awaitable, Coroutine, Union

import asyncio

from redisauth.err import RequestTokenErr, TokenRenewalErr
from redisauth.idp import IdentityProviderInterface
from redisauth.token import TokenResponse


class CredentialsListener:
    """
    Listeners that will be notified on events related to credentials.
    Accepts callbacks and awaitable callbacks.
    """
    def __init__(self):
        self._on_next = None
        self._on_error = None

    @property
    def on_next(self) -> Union[Callable[[Any], None], Awaitable]:
        return self._on_next

    @on_next.setter
    def on_next(self, callback: Union[Callable[[Any], None], Awaitable]) -> None:
        self._on_next = callback

    @property
    def on_error(self) -> Union[Callable[[Exception], None], Awaitable]:
        return self._on_error

    @on_error.setter
    def on_error(self, callback: Union[Callable[[Exception], None], Awaitable]) -> None:
        self._on_error = callback


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

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Run loop in a separate thread to unblock main thread.
            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=_start_event_loop_in_thread,
                args=(loop,),
                daemon=True
            )
            thread.start()

        # Event to block for initial execution.
        init_event = asyncio.Event()
        self._init_timer = loop.call_later(
            initial_delay_in_ms / 1000,
            self._renew_token,
            init_event
        )

        if block_for_initial:
            # Blocks in thread-safe maner.
            asyncio.run_coroutine_threadsafe(init_event.wait(), loop).result()

        return self.stop

    async def start_async(
            self,
            listener: CredentialsListener,
            block_for_initial: bool = False,
            initial_delay_in_ms: float = 0,
    ) -> Callable[[], Coroutine[Any, Any, None]]:
        self._listener = listener

        loop = asyncio.get_running_loop()
        init_event = asyncio.Event()

        # Wraps the async callback with async wrapper to schedule with loop.call_later()
        wrapped = _async_to_sync_wrapper(loop, self._renew_token_async, init_event)
        self._init_timer = loop.call_later(initial_delay_in_ms / 1000, wrapped)

        if block_for_initial:
            await init_event.wait()

        return self.stop_async

    def stop(self):
        if self._next_timer is not None:
            self._next_timer.cancel()

    async def stop_async(self):
        return self.stop()

    def acquire_token(self, force_refresh=False) -> TokenResponse:
        try:
            token = self._idp.request_token(force_refresh)
        except RequestTokenErr as e:
            if self._retries < self._config.get_retry_policy().get_max_attempts():
                self._retries += 1
                sleep(self._config.get_retry_policy().get_delay_in_ms() / 1000)
                return self.acquire_token(force_refresh)
            else:
                raise e

        self._retries = 0
        return TokenResponse(token)

    async def acquire_token_async(self, force_refresh=False) -> TokenResponse:
        try:
            token = self._idp.request_token(force_refresh)
        except RequestTokenErr as e:
            if self._retries < self._config.get_retry_policy().get_max_attempts():
                self._retries += 1
                await asyncio.sleep(self._config.get_retry_policy().get_delay_in_ms() / 1000)
                return await self.acquire_token_async(force_refresh)
            else:
                raise e

        self._retries = 0
        return TokenResponse(token)

    def _calculate_renewal_delay(self, expire_date: float, issue_date: float) -> float:
        delay_for_lower_refresh = self._delay_for_lower_refresh(expire_date)
        delay_for_ratio_refresh = self._delay_for_ratio_refresh(expire_date, issue_date)
        delay = min(delay_for_ratio_refresh, delay_for_lower_refresh)

        return 0 if delay < 0 else delay / 1000

    def _delay_for_lower_refresh(self, expire_date: float):
        return (expire_date - self._config.get_lower_refresh_bound_millis() -
                (datetime.now(timezone.utc).timestamp() * 1000))

    def _delay_for_ratio_refresh(self, expire_date: float, issue_date: float):
        token_ttl = expire_date - issue_date
        refresh_before = token_ttl - (token_ttl * self._config.get_expiration_refresh_ratio())

        return expire_date - refresh_before - (datetime.now(timezone.utc).timestamp() * 1000)

    def _renew_token(self, init_event: asyncio.Event = None):
        """
        Task to renew token from identity provider.
        Schedules renewal tasks based on token TTL.
        """

        try:
            token_res = self.acquire_token(force_refresh=True)
            delay = self._calculate_renewal_delay(
                token_res.get_token().get_expires_at_ms(),
                token_res.get_token().get_received_at_ms()
            )

            if token_res.get_token().is_expired():
                raise TokenRenewalErr("Requested token is expired")

            # If reference was already cleared by GC, return current token.
            if self._listener.on_next is None or self._listener.on_next() is None:
                return

            try:
                self._listener.on_next()(token_res.get_token())
            except Exception as e:
                raise TokenRenewalErr(e)

            if delay <= 0:
                return

            loop = asyncio.get_running_loop()
            self._next_timer = loop.call_later(delay, self._renew_token)
            return token_res
        except Exception as e:
            if self._listener.on_error is None or self._listener.on_error() is None:
                raise e

            self._listener.on_error()(e)
        finally:
            if init_event:
                init_event.set()

    async def _renew_token_async(self, init_event: asyncio.Event = None):
        """
        Async task to renew tokens from identity provider.
        Schedules renewal tasks based on token TTL.
        """

        try:
            token_res = await self.acquire_token_async(force_refresh=True)
            delay = self._calculate_renewal_delay(
                token_res.get_token().get_expires_at_ms(),
                token_res.get_token().get_received_at_ms()
            )

            if token_res.get_token().is_expired():
                raise TokenRenewalErr("Requested token is expired")

            # If reference was already cleared by GC, return current token.
            if self._listener.on_next is None or self._listener.on_next() is None:
                return

            try:
                await self._listener.on_next()(token_res.get_token())
            except Exception as e:
                raise TokenRenewalErr(e)

            if delay <= 0:
                return

            loop = asyncio.get_running_loop()
            wrapped = _async_to_sync_wrapper(loop, self._renew_token_async)
            loop.call_later(delay, wrapped)
        except Exception as e:
            if init_event:
                init_event.set()

            if self._listener.on_error is None or self._listener.on_error() is None:
                raise e

            await self._listener.on_error()(e)
        finally:
            if init_event:
                init_event.set()


def _async_to_sync_wrapper(loop, coro_func, *args, **kwargs):
    """
    Wraps an asynchronous function so it can be used with loop.call_later.

    :param loop: The event loop in which the coroutine will be executed.
    :param coro_func: The coroutine function to wrap.
    :param args: Positional arguments to pass to the coroutine function.
    :param kwargs: Keyword arguments to pass to the coroutine function.
    :return: A regular function suitable for loop.call_later.
    """

    def wrapped():
        # Schedule the coroutine in the event loop
        asyncio.ensure_future(coro_func(*args, **kwargs), loop=loop)

    return wrapped


def _start_event_loop_in_thread(event_loop: asyncio.AbstractEventLoop):
    """
    Starts event loop in a thread.
    Used to be able to schedule tasks using loop.call_later.

    :param event_loop:
    :return:
    """
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()


def _wait_for_event(event: asyncio.Event):
    async def wait():
        await event.wait()

    asyncio.run(wait())
