import sys

from app.services.admin import intelligence as _module

sys.modules[__name__] = _module
