from redisauth.entraid import EntraIdIdentiyProvider
from unittest import TestCase
import os


class EntraIdIdpTest(TestCase):
    def test_retrive_token(self):
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        self.assertTrue(tenant_id)

        idp = EntraIdIdentiyProvider(tenant_id, client_id, client_secret)
        token = idp.request_token()

        self.assertTrue(token.value)
        print("token_value = {}".format(token.value))

        self.assertTrue(token.meta)
        print("token_meta = {}".format(token.meta))

        self.assertNotEquals(token.expires_at, -1)
        print("token_exp = {}".format(token.expires_at))
