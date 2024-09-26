'''
An error message that indicates that the authentication with the identity provider couldn't be established.
'''

class ErrNotAuthenticated(Exception):
    def __init__(self):
        super().__init__("You are not authenticated.")


'''
An error message that tells you that an error occurred when receiving the token.
'''
class ErrCantReceiveToken(Exception):
    def __init__(self):
        super().__init__("Can't receive a token from the IDP.")