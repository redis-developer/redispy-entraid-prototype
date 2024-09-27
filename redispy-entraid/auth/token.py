import jwt
from datetime import datetime, timezone

'''
A token has a 

- An decoded value
- An expected date/time of expiration
- A method that allows calculating its time to live

'''
class Token:
    def __init__(self, value, exp):
        self.value = value
        self.exp = exp
        self.meta = {}

    '''
    Calculate how the token has still to live
    '''
    def ttl(self):
        return self.exp - datetime.utcnow()


    '''
    Indicates if the token should be seen as expired.
    
    This method is intended to be overridden if the identity provider offers more sophisticated
    methods.
    '''
    def is_expired(self) -> bool:
        return self.ttl() <= 0




'''
A JSON Web Token has meta data encoded as JSON
'''
class JWToken(Token):
    def __init__(self, value, exp=-1):
        super().__init__(value, exp)
        self.meta = self._decode_meta()

        # If the time to live wasn't given, then try to derive it from the JWT token
        if exp == -1:
            self.exp = self.meta['exp']

    '''
    Decode the token meta data
    '''
    def _decode_meta(self):
            return jwt.decode(self.value, options={"verify_signature": False})

