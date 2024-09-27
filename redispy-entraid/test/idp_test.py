from unittest import TestCase
from auth.idp import FakeIdentiyProvider


class FakeIdpTest(TestCase):
    def test_auth_success(self):
        idp = FakeIdentiyProvider("testuser", "password")
        self.assertTrue(idp.authenticate())
        self.assertTrue(idp.is_authenticated)

        token = idp.request_token().value
        print("\ntoken = {}".format(token))
        self.assertTrue(token)


    def test_auth_failed(self):
        idp = FakeIdentiyProvider("testuser", "wrongpass")
        self.assertFalse(idp.authenticate())
        self.assertFalse(idp.is_authenticated)

        try:
            idp.request_token().value
        except Exception as err:
            self.assertEqual("You are not authenticated.", str(err))

