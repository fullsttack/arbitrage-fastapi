# Import all settings from base
from .base import *

# Import development settings if in development mode
try:
    from .development import *
except ImportError:
    pass
