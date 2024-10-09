import threading
from time import sleep
from redisauth.err import ErrInvalidTokenMgrConfig
from redisauth.idp import IdentityProviderInterface
from redisauth.token import Token
import logging

'''
  This configuration tells the token manager how tokens should be proactively considered as expired

  ttl_min_ratio - The minimum time to live as ratio of the overall lifespan before considering tokens as expired
  ttl_min_time - The minimum time to live in seconds before considering a token as expired
  check_interval - The number of seconds to wait before checking the next time for token expiration
'''
class TokenManagerConfig():
    def __init__(self, ttl_min_time = -1, ttl_min_ratio = -1, check_interval = 1):
        self.ttl_min_ratio = ttl_min_ratio
        self.ttl_min_time = ttl_min_time
        self.check_interval = check_interval


'''
Listens to token expirations
'''
class TokenExpiryListener:
    def __init__(self):
        self.callbacks = []

    # Add listener callback function
    def add_callback(self, callback):
        self.callbacks.append(callback)

    def on_token_renewed(self, token):
        for cb in self.callbacks:
            cb(token)


'''
A job that notifies when tokens are renewed
'''
class TokenManager:
    def __init__(self, identiy_provider : IdentityProviderInterface, config=TokenManagerConfig()):
        self.idp = identiy_provider
        self.config = config
        self._token_mgr_thread = None
        self._is_running = False


    '''
    Monitors the tokens within a thread
    '''
    def _monitor_token(self, token : Token, listener : TokenExpiryListener):

        while self._is_running:
            # Check if the token is expired based on the configuration
            # If the default config is used, then we leave it to the token implementation to tell us if the token is expired
            is_expired = False

            if not token:
                is_expired = True
            else:
                logging.debug("ttl = {}".format(token.ttl()))
                print("ttl = {}".format(token.ttl()))

                if self.config.ttl_min_ratio == -1 and self.config.ttl_min_time == -1:
                    is_expired = token.is_expired()
                elif self.config.ttl_min_time != -1:
                    is_expired = (token.ttl() <= self.config.ttl_min_time)
                # Not every token implementation has a ttl_max property. We should check if the configuration makes sense
                elif self.config.ttl_min_ratio != -1:
                    if hasattr(token, 'ttl_max') and not is_expired:
                        is_expired = (token.ttl() / token.ttl_max <= self.config.ttl_min_ratio)
                    else:
                        raise ErrInvalidTokenMgrConfig()

            # Refresh the token if it is expired and wait a second
            if is_expired:
                token = self.idp.request_token()
                listener.on_token_renewed(token)

            sleep(self.config.check_interval)


    '''
    Start the token manager job
    '''
    def start(self, listener, block_for_initial = True):
        initial_token = None

        if block_for_initial:
            initial_token = self.idp.request_token()
            listener.on_token_renewed(initial_token)

        self._token_mgr_thread = threading.Thread(target=self._monitor_token, args=(initial_token, listener))
        self._is_running = True
        self._token_mgr_thread.start()


    '''
    Terminate the token manager job
    '''
    def stop(self):
        self._is_running = False
        self._token_mgr_thread = None






