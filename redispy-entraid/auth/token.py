import jwt
from datetime import datetime

'''
A token has a 

- An decoded value
- An expected date/time of expiration
- A method that allows calculating its time to live

'''
class Token:
    def __init__(self, value, expires_at = -1,  received_at = datetime.utcnow().timestamp()):
        self.value = value
        self.expires_at = expires_at
        self.received_at = received_at
        self.meta = {}

    '''
    Calculate how the token has still to live
    '''
    def ttl(self):
        return self.expires_at - datetime.utcnow().timestamp()


    '''
    Indicates if the token should be seen as expired.
    
    This method is intended to be overridden if the identity provider offers more sophisticated
    methods.
    '''
    def is_expired(self) -> bool:
        return self.ttl() <= 0


    '''
    Checks if the token is still valid.
    
    This method is intended to be overridden if the identity provider offers mechanisms beyond checking
    the expiration time (e.g., checking signatures)
    '''
    def is_valid(self) -> bool:
        return self.is_expired()




'''
A JSON Web Token has meta data encoded as JSON
'''
class JWToken(Token):
    def __init__(self, value, expires_at = -1,  received_at = datetime.utcnow().timestamp()):
        super().__init__(value, expires_at, received_at)
        self.meta = self._decode_meta()

        # If the expiration time is not given, then try to derive it from the JWT token
        if expires_at == -1:
            self.expires_at = self.meta['exp']

    '''
    Decode the token meta data
    '''
    def _decode_meta(self):
            return jwt.decode(self.value, options={"verify_signature": False})

