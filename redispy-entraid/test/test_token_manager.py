from datetime import datetime, timezone
from time import sleep
from unittest.mock import Mock

import pytest
from redisauth.idp import IdentityProviderInterface
from redisauth.token_manager import (
    Observable,
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
            (0.4, 3),
            (0.28, 4),
        ],
        ids=[
            "Refresh ratio = 0.9,  2 tokens in 0,1 second",
            "Refresh ratio = 0.4,  3 tokens in 0,1 second",
            "Refresh ratio = 0.28, 4 tokens in 0,1 second",
        ]
    )
    def test_success_token_renewal(self, exp_refresh_ratio, tokens_refreshed):
        tokens = []
        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.return_value = SimpleToken(
            'value',
            (datetime.now(timezone.utc).timestamp() / 1000) + 0.1,
            (datetime.now(timezone.utc).timestamp() / 1000),
            []
        )

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        mock_listener = Mock(spec=Observable)
        mock_listener.on_next = on_next

        retry_policy = RetryPolicy(1, 10)
        config = TokenManagerConfig(exp_refresh_ratio, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        sleep(0.1)

        assert len(tokens) == tokens_refreshed

    def test_success_token_renewal_with_retry(self):
        tokens = []
        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.side_effect = [
            Exception,
            Exception,
            SimpleToken(
                'value',
                (datetime.now(timezone.utc).timestamp() / 1000) + 0.1,
                (datetime.now(timezone.utc).timestamp() / 1000),
                []
            )
        ]

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        mock_listener = Mock(spec=Observable)
        mock_listener.on_next = on_next

        retry_policy = RetryPolicy(3, 10)
        config = TokenManagerConfig(1, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        sleep(0.1)

        assert mock_provider.request_token.call_count == 3
        assert len(tokens) == 1

    def test_success_token_renewal_with_on_complete(self):
        tokens = []
        is_complete = False
        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.return_value = SimpleToken(
            'value',
            (datetime.now(timezone.utc).timestamp() / 1000) + 0.1,
            (datetime.now(timezone.utc).timestamp() / 1000),
            []
        )

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        def on_completed():
            nonlocal is_complete
            is_complete = True

        mock_listener = Mock(spec=Observable)
        mock_listener.on_next = on_next
        mock_listener.on_completed = on_completed

        retry_policy = RetryPolicy(1, 10)
        config = TokenManagerConfig(0.9, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        sleep(0.1)
        mgr.stop()

        assert len(tokens) == 2
        assert is_complete is True


    def test_failed_token_renewal_with_retry(self):
        tokens = []
        exceptions = []

        mock_provider = Mock(spec=IdentityProviderInterface)
        mock_provider.request_token.side_effect = [
            Exception,
            Exception,
            Exception
        ]

        def on_next(token):
            nonlocal tokens
            tokens.append(token)

        def on_error(exception):
            nonlocal exceptions
            exceptions.append(exception)

        mock_listener = Mock(spec=Observable)
        mock_listener.on_next = on_next
        mock_listener.on_error = on_error

        retry_policy = RetryPolicy(3, 10)
        config = TokenManagerConfig(1, 0, 1000, retry_policy)
        mgr = TokenManager(mock_provider, config)
        mgr.start(mock_listener)
        sleep(0.1)

        assert mock_provider.request_token.call_count == 4
        assert len(tokens) == 0
        assert len(exceptions) == 1