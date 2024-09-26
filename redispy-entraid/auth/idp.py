import jwt
from datetime import datetime, timedelta
from auth.token import Token, JWToken
from auth.err import ErrNotAuthenticated

'''
This interface is the facade of an identity provider
'''
class IdentityProviderInterface:

    def __init__(self, creds):
        self.creds = creds
        self.is_authenticated = self.authenticate(creds)

    '''
    Authenticate with the identity provider by using the credentials
    
    If no credentials are passed, then the original credentials are used.
    '''
    def authenticate(self, creds=None) -> bool:
        pass

    '''
    Receive a token from the identity provider. Receiving a token only works when being authenticated.
    '''
    def receive_token(self):
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

    def receive_token(self) -> Token:
        if self.is_authenticated:
            payload = {
                "user_id": 123,
                "username": "testuser",
                "exp": datetime.utcnow() + timedelta(minutes=30)
            }

            value = jwt.encode(payload, self.SIGN, "HS256")

            return JWToken(value)
        else:
            raise ErrNotAuthenticated()