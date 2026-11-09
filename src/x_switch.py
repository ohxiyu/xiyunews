"""One operator switch shared by the dependency-free gate and sender."""
import os


def effective_enabled(default=False, env=None):
    value=(os.environ if env is None else env).get('X_DELIVERY_ENABLED','').strip()
    if not value:return default is True
    if value=='true':return True
    if value=='false':return False
    raise ValueError('X_DELIVERY_ENABLED must be true, false, or empty')
