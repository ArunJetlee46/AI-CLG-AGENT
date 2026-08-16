import sys

from app.services.placement import intelligence as _module

sys.modules[__name__] = _module
