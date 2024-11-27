class RequestTokenErr(Exception):
    """
    Exception thrown when a request token is invalid.
    """
    def __init__(self, *args):
        super().__init__(*args)