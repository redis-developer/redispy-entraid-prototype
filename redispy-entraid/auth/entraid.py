from pycparser.ply.yacc import token

from auth.idp import IdentityProviderInterface
from auth.err import  ErrNotAuthenticated, ErrCantReceiveToken
from enum import Enum
from msal import ConfidentialClientApplication
from auth.token import JWToken

'''
The authentication methods that are supported by our identity provider implementation
'''
class AuthMethods(Enum):
    SERVICE_PRINCIPAL = 1

'''
A credentials dictionary which is prefilled with some common EntraId properties
'''
class EntraIdCreds(dict):
    def __init__(self):
        super().__init__()
        self["authority_url"] = "https://login.microsoftonline.com"
        self["scope"] = "https://redis.azure.com/.default"


'''
An EntraID token is a JWT token, whereby it has an 'iat` meta data property that tells us when the token was issued.
We can use this information to leverage a threshold (percentage of the maximum time to live), 
to proactively recognize the token as being expired.
'''
class EntraIdToken(JWToken):
    def __init__(self, value, thr=0.25):
        super().__init__(value)
        self.thr = thr
        self.issued_at = self.meta["iat"]
        self.ttl_max = self.exp - self.issued_at

    '''
    This method overrides the standard behaviour of 'is_expired'. We assume that the token is expired before 
    we hit the actual expiration time if the token reached 25% (default value) of its maximum time to live.
    '''
    def is_expired(self) -> bool:
        return self.ttl() / self.ttl_max <= self.thr

'''
The EntraId identity provider. 
 
An implementation of the IdentityProviderInterface needs to do the following: 

1. Construct the dictionary of credentials
2. Pass it to the super constructor
3. Override the 'authenticate' method
'''
class EntraIdIdentiyProvider(IdentityProviderInterface):
    def __init__(self, tenant_id, client_id, client_secret, scope=None):
        creds = EntraIdCreds()
        creds["type"] = AuthMethods.SERVICE_PRINCIPAL.name
        creds["tenant_id"]  = tenant_id
        creds["client_id"] = client_id
        creds["client_secret"] = client_secret

        '''
        Override the scope if it was passed over. It's required that the scope is configurable, whereby
        the Redis scope is normally https://redis.azure.com/.default.
        '''
        if scope:
            creds["scope"] = scope

        # Calls authenticate
        super().__init__(creds)

    '''
    Authenticate by using the Microsoft authentication library
    '''
    def authenticate(self, creds = None) -> bool:
        success = False

        # Use the original creds unless they are overridden
        if not creds:
            creds = self.creds

        if creds.get("type") == AuthMethods.SERVICE_PRINCIPAL.name:
            # Authenticate via a service principal / client application
            try:
                self.app = ConfidentialClientApplication(creds.get("client_id"),
                                                         creds.get("client_secret"),
                                                         "{}/{}".format(creds.get("authority_url"),
                                                                        creds.get("tenant_id"))
                                                         )

                # Let's assume that the authentication was successful if we can acquire a token
                scopes = [ creds.get("scope") ]
                token_dict = self.app.acquire_token_for_client(scopes)
                if "access_token" in token_dict:
                    success = True
            except Exception as e:
                #TODO: Add logging
                print(e)

        self.is_authenticated = success
        return success


    '''
    Receive a token from EntraId
    '''
    def receive_token(self):
        if not self.is_authenticated:
            raise ErrNotAuthenticated()
        try:
            scopes = [self.creds.get("scope")]
            token_value = self.app.acquire_token_for_client(scopes)["access_token"]
            return EntraIdToken(token_value)
        except Exception as e:
            #TODO: Add logging
            print(e)
            raise ErrCantReceiveToken()












