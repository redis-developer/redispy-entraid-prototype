from pycparser.ply.yacc import token
from redis import Redis

from redisauth.token import Token
from redisauth.tokenmgr import TokenManager, TokenExpiryListener
import redis


'''
The connection manager is responsible for reauthenticating the connections when tokens need to be
refreshed
'''
class ConnectionManager:
    def __init__(self, token_manager : TokenManager, client : Redis):
        self.token_manager = token_manager
        self.client = client

    '''
    Starts the connection manager
    '''
    def start(self):
        listener = TokenExpiryListener()
        listener.add_callback(self._token_refreshed_callback)
        listener.add_err_callback(self._token_refresh_err_callback)
        self.token_manager.start(listener, True)

    '''
    This callback is going to be used by the token manager's thread
    '''
    def _token_refreshed_callback(self, token):
        self.authenticate_connection(self.client, token)

    '''
    This callback gets invoked the token manager faces an error
    '''
    def _token_refresh_err_callback(self, error):
        print(error)

    def authenticate_connection(self, client : redis.Redis, token : Token):

        # -- TODO
        # The standalone client uses a connection pool behind the scenes.
        pool = client.connection_pool

        # We need to reauthenticate on the available and the connections that are in use
        for  conn in pool._available_connections:
            print("TODO: Authenticate")

        for conn in pool._in_use_connections:
            print("TODO: Authenticate")
            '''
            1. The connection manager thread aquires a soft lock
            2. The other thread completes the next command execution, but doen't execute the command. Instead it needs
               to implement a lock wait (for n milliseconds) 
            3. As soon as the reauthentication is successully completed. the soft lock is reset again.
            
            Alternatively: Use a synchronous approach instead of an event-driven one for both the token manager and the
            connection manager.
            '''


