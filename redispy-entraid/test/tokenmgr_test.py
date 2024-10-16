import threading
from time import sleep
from redisauth.entraid import EntraIdIdentiyProvider
from redisauth.idp import FakeIdentiyProvider
from redisauth.tokenmgr import TokenExpiryListener, TokenManagerConfig
from unittest import TestCase
import os

from redisauth.tokenmgr import TokenManager


'''
Function to check if we can automatically stop the token manager if it is no longer referenced
'''
def run_token_manager():
    print("-- run_token_manager START")
    token_mgr = TokenManager(FakeIdentiyProvider("testuser", "password"), TokenManagerConfig())
    token_mgr.start(TokenExpiryListener())
    print("Keep the function running for about 5 seconds.")
    sleep(5)
    print("-- run_token_manager EXIT")


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
        token_mgr_config = TokenManagerConfig(ttl_min_time=10790, check_interval=1)
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

    def  test_token_mrg_disposal(self):
        self.assertEqual(1, threading.active_count())
        run_token_manager()
        print("After the function exited wait up to 5 seconds to let the garbage collector clean the manager and its thread.")
        sleep(5)
        self.assertEqual(1, threading.active_count())



