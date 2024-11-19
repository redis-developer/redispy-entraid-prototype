from unittest import TestCase
from redis import Redis
from redisauth.connmgr import ConnectionManager
from redisauth.idp import FakeIdentiyProvider
from redisauth.tokenmgr import TokenManager, TokenManagerConfig


class ConnManagerTest(TestCase):

    def test_connmgr(self):

        # TODO
        idp = FakeIdentiyProvider('testuser', 'password')
        token = idp.request_token()
        print(token)

        token_mgr = TokenManager(idp, TokenManagerConfig())
        conn_mgr = ConnectionManager(token_mgr, Redis())
        conn_mgr.start()
        # sleep(60)

