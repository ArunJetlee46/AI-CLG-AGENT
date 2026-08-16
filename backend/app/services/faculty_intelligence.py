import sys

from app.services.faculty import intelligence as _module

sys.modules[__name__] = _module
