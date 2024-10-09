import threading
from time import sleep

from pycparser.ply.yacc import token

from redisauth.entraid import EntraIdIdentiyProvider
from redisauth.tokenmgr import TokenExpiryListener, TokenManagerConfig
from unittest import TestCase

import os

from redisauth.tokenmgr import TokenManager


class TokenManagerTest(TestCase):

    def __init__(self, *args, **kwargs):
        super(TokenManagerTest, self).__init__(*args, **kwargs)
        self.callback_invoked = False

    def printing_callback(self, token):
        print("-- printing callback")
        print("ttl = {}, value = {}".format(token.ttl(), token.value))
        self.callback_invoked = True

    def test_token_mrg_job(self):

        # Create the IDP
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        self.assertTrue(tenant_id)
        idp = EntraIdIdentiyProvider(tenant_id, client_id, client_secret)

        # EntraId tokens have TTL of 3 hours. So, let's mimic to expire them after 10 seconds
        token_mgr_config = TokenManagerConfig(ttl_min_time=10790, check_interval=2)
        token_mgr = TokenManager(idp, token_mgr_config)
        listener = TokenExpiryListener()
        listener.add_callback(self.printing_callback)
        self.assertFalse(self.callback_invoked)
        self.assertEqual(1, threading.active_count())
        token_mgr.start(listener)
        self.assertEqual(2, threading.active_count())

        # Sleep more than 10 seconds
        sleep(15)
        self.assertTrue(self.callback_invoked)
        token_mgr.stop()

        # It might a cycle to stop the thread
        sleep(5)
        self.assertEqual(1, threading.active_count())



