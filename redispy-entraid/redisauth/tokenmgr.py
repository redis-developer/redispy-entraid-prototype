import threading
from time import sleep
from redisauth.err import ErrInvalidTokenMgrConfig
from redisauth.idp import IdentityProviderInterface
from redisauth.token import Token
import logging
import weakref

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
        self.err_callbacks = []

    # Add listener callback function
    def add_callback(self, callback):
        self.callbacks.append(callback)

    def add_err_callback(self, callback):
        self.err_callbacks.append(callback)

    def on_token_renewed(self, token : Token):
        for cb in self.callbacks:
            cb(token)

    def on_token_renew_err(self, error : Exception):
        for cb in self.err_callbacks:
            cb(error)



'''
Monitors the tokens within a thread

This function would typically belong to the token manager, but we want the thread end when garbage collection kicks in.
So we need to use a weak reference instead of using a class method. 
'''
def _monitor_token(weak_mgr_ref, token : Token, listener : TokenExpiryListener):

        while True:
            # Resolve the weak reference to the actual token manager
            mgr = weak_mgr_ref()

            # A bit dirty, but not all Python versions allow assigning variables within a while loop.
            if (mgr is None) or (mgr._stop_event.isSet()):
                break

            try:
                # Check if the token is expired based on the configuration
                # If the default config is used, then we leave it to the token implementation to tell us if the token is expired
                is_expired = False

                if not token:
                    is_expired = True
                else:
                    logging.debug("ttl = {}".format(token.ttl()))

                    if mgr.config.ttl_min_ratio == -1 and mgr.config.ttl_min_time == -1:
                        is_expired = token.is_expired()
                    elif mgr.config.ttl_min_time != -1:
                        is_expired = (token.ttl() <= mgr.config.ttl_min_time)
                    # Not every token implementation has a ttl_max property. We should check if the configuration makes sense
                    elif mgr.config.ttl_min_ratio != -1:
                        if hasattr(token, 'ttl_max') and not is_expired:
                            is_expired = (token.ttl() / token.ttl_max <= mgr.config.ttl_min_ratio)
                        else:
                            raise ErrInvalidTokenMgrConfig()

                # Refresh the token if it is expired and wait a second
                if is_expired:
                    token = mgr.idp.request_token()
                    listener.on_token_renewed(token)

                sleep(mgr.config.check_interval)

            except Exception as error:
                listener.on_token_renew_err(error)

            # Get rid of the manager reference to allow the garbage collector to clean it up.
            mgr = None


'''
A job that notifies when tokens are renewed
'''
class TokenManager:
    def __init__(self, identify_provider : IdentityProviderInterface, config=TokenManagerConfig()):
        self.idp = identify_provider
        self.config = config
        self._token_mgr_thread = None
        self._stop_event = threading.Event()

    def __del__(self):
        logging.debug("Disposed the TokenManager")
        self.stop()


    '''
    Start the token manager job
    '''
    def start(self, listener, block_for_initial = True):
        initial_token = None

        if block_for_initial:
            initial_token = self.idp.request_token()
            listener.on_token_renewed(initial_token)

        # Avoid that the thread has a back reference o the token manager
        weak_mgr_ref = weakref.ref(self)

        # Setting daemon to True guarantees that the thread is killed as soon as the main thread is terminated.
        self._token_mgr_thread = threading.Thread(target=_monitor_token, args=(weak_mgr_ref, initial_token, listener),
                                                  daemon=True)
        self._token_mgr_thread.start()

    '''
    Terminate the token manager job
    '''
    def stop(self):
        self._stop_event.set()
        if self._token_mgr_thread is not None:
            self._token_mgr_thread.join()  # Wait for the thread to finish
            self._token_mgr_thread = None





