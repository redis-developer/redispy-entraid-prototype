from redisauth.tokenmgr import TokenManager

'''
The connection manager is responsible for reauthenticating the connections when tokens need to be
refreshed
'''
class ConnectionManager():
    def __init__(self, token_manager : TokenManager):
        self.token_manager = token_manager





