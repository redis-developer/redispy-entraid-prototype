from auth.idp import IdentityProviderInterface
from auth.token import Token

'''
  This configuration tells the token manager how tokens should be proactively considered as expired

  ttl_min_ratio - The minimum time to live as ratio of the overall lifespan before considering tokens as expired
  ttl_min_time - The minumum time to live in seconds of the overall lifetime before considering tokens as expired
'''
class TokenManagerConfig():
    def __init__(self, ttl_min_ratio, ttl_min_time):
        self.ttl_min_ratio = ttl_min_ratio
        self.ttl_min_time = ttl_min_time

'''
The default leaves it to the token implementation to tell when the token is expired
'''
class DefaultTokenManagerConfig(TokenManagerConfig):
    def __init__(self):
        super().__init__(-1, -1)


'''
A job that notifies when tokens are renewed
'''
class TokenManager:
    def __init__(self, identiy_provider, config=DefaultTokenManagerConfig()):
        self.idp = identiy_provider
        self.config = config

    '''
    Start the token manager job
    '''
    def start(self, block_for_initial = True):
        pass


    '''
    Terminate the token manager job
    '''
    def stop(self):
        pass
