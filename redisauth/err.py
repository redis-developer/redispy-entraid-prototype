'''
An error message that indicates that the authentication with the identity provider couldn't be established.
'''

class ErrNotAuthenticated(Exception):
    def __init__(self):
        super().__init__("You are not authenticated.")


class RequestTokenErr(Exception):
    """
    Exception thrown when a request token is invalid.
    """
    def __init__(self, *args):
        super().__init__(*args)


class ErrInvalidTokenMgrConfig(Exception):
    def __init__(self):
        super().__init__("This token manager configuration can't be used with the given token implementation.")
