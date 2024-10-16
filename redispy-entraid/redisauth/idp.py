import jwt
from datetime import datetime, timedelta
from redisauth.token import Token, JWToken
from redisauth.err import ErrNotAuthenticated

'''
This interface is the facade of an identity provider
'''
class IdentityProviderInterface:

    def __init__(self, creds):
        self.is_authenticated = self.authenticate(creds)

    '''
    Authenticate with the identity provider by using the credentials.
    '''
    def authenticate(self, creds) -> bool:
        pass

    '''
    Receive a token from the identity provider. Receiving a token only works when being authenticated.
    '''
    def request_token(self):
        pass



'''
A very simple fake identity provider for testing purposes
'''
class FakeIdentiyProvider(IdentityProviderInterface):

    SIGN = "secret"

    '''
    Initialize by authenticating
    '''
    def __init__(self, user, password):
        self.creds = { 'user' : user, 'password' : password}
        super().__init__(self.creds)

    def authenticate(self, creds=None) -> bool:

        if not creds:
            creds = self.creds

        if creds['user'] == "testuser" and creds['password'] == "password":
            return True

        return False

    def request_token(self) -> Token:
        if self.is_authenticated:
            payload = {
                "user_id": 123,
                "username": "testuser",
                "exp": datetime.utcnow() + timedelta(seconds=10)
            }

            value = jwt.encode(payload, self.SIGN, "HS256")

            return JWToken(value)
        else:
            raise ErrNotAuthenticated()