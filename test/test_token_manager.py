import weakref
from datetime import datetime, timezone
from time import sleep
from unittest.mock import Mock

import pytest

from redisauth.err import RequestTokenErr
from redisauth.idp import IdentityProviderInterface
from redisauth.token_manager import (
    CredentialsListener,
    TokenManagerConfig,
    RetryPolicy,
    TokenManager
)
from redisauth.token import SimpleToken


class TestTokenManager:
    @pytest.mark.parametrize(
        "exp_refresh_ratio,tokens_refreshed",
        [
            (0.9, 2),
            (0.28, 4),
        ],
        ids=[
            "Refresh ratio = 0.9,  2 tokens in 0,1 second",
            "Refresh ratio = 0.28, 4 tokens in 0,1 second",
        ]
    )
    def test_success_token_renewal(self, exp_refresh_ratio, tokens_refreshed):
        tokens = []
        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.side_effect = [
            SimpleToken(
                'value',
                (datetime.now(timezone.utc).timestamp() * 1000) + 100,
                (datetime.now(timezone.utc).timestamp() * 1000),
            {"oid": 'test'}),
            SimpleToken(
                'value',
                (datetime.now(timezone.utc).timestamp() * 1000) + 130,
                (datetime.now(timezone.utc).timestamp() * 1000) + 30,
                {"oid": 'test'}),
            SimpleToken(
                'value',
                (datetime.now(timezone.utc).timestamp() * 1000) + 160,
                (datetime.now(timezone.utc).timestamp() * 1000) + 60,
                {"oid": 'test'}),
            SimpleToken(
                'value',
                (datetime.now(timezone.utc).timestamp() * 1000) + 190,
                (datetime.now(timezone.utc).timestamp() * 1000) + 90,
                {"oid": 'test'}),
        ]

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        mock_listener = Mock(spec=CredentialsListener)
        mock_listener.on_next = weakref.ref(on_next)

        retry_policy = RetryPolicy(1, 10)
        config = TokenManagerConfig(exp_refresh_ratio, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        sleep(0.1)

        assert len(tokens) == tokens_refreshed

    @pytest.mark.parametrize(
        "block_for_initial,tokens_acquired",
        [
            (True, 1),
            (False, 0),
        ],
        ids=[
            "Block for initial, callback will triggered once",
            "Non blocked, callback wont be triggered",
        ]
    )
    def test_request_token_blocking_behaviour(self, block_for_initial, tokens_acquired):
        tokens = []
        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.return_value = SimpleToken(
            'value',
            (datetime.now(timezone.utc).timestamp() * 1000) + 100,
            (datetime.now(timezone.utc).timestamp() * 1000),
            {"oid": 'test'}
        )

        def on_next(token):
            nonlocal tokens
            sleep(0.1)
            tokens.append(token)

        mock_listener = Mock(spec=CredentialsListener)
        mock_listener.on_next = weakref.ref(on_next)

        retry_policy = RetryPolicy(1, 10)
        config = TokenManagerConfig(1, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener, block_for_initial=block_for_initial)

        assert len(tokens) == tokens_acquired

    def test_success_token_renewal_with_retry(self):
        tokens = []
        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.side_effect = [
            RequestTokenErr,
            RequestTokenErr,
            SimpleToken(
                'value',
                (datetime.now(timezone.utc).timestamp() * 1000) + 100,
                (datetime.now(timezone.utc).timestamp() * 1000),
                {"oid": 'test'}
            )
        ]

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        mock_listener = Mock(spec=CredentialsListener)
        mock_listener.on_next = weakref.ref(on_next)

        retry_policy = RetryPolicy(3, 10)
        config = TokenManagerConfig(1, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        # Should be less than a 0.1, or it will be flacky due to additional token renewal.
        sleep(0.08)

        assert mock_provider.request_token.call_count == 3
        assert len(tokens) == 1

    def test_no_token_renewal_on_process_complete(self):
        tokens = []
        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.return_value = SimpleToken(
            'value',
            (datetime.now(timezone.utc).timestamp() * 1000) + 1000,
            (datetime.now(timezone.utc).timestamp() * 1000),
            {"oid": 'test'}
        )

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        mock_listener = Mock(spec=CredentialsListener)
        mock_listener.on_next = weakref.ref(on_next)

        retry_policy = RetryPolicy(1, 10)
        config = TokenManagerConfig(0.9, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        sleep(0.2)

        assert len(tokens) == 1

    def test_failed_token_renewal_with_retry(self):
        tokens = []
        exceptions = []

        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.side_effect = [
            RequestTokenErr,
            RequestTokenErr,
            RequestTokenErr,
            RequestTokenErr,
        ]

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        def on_error(exception):
            nonlocal exceptions
            exceptions.append(exception)

        mock_listener = Mock(spec=CredentialsListener)
        mock_listener.on_next = weakref.ref(on_next)
        mock_listener.on_error = weakref.ref(on_error)

        retry_policy = RetryPolicy(3, 10)
        config = TokenManagerConfig(1, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        sleep(0.1)

        assert mock_provider.request_token.call_count == 4
        assert len(tokens) == 0
        assert len(exceptions) == 1