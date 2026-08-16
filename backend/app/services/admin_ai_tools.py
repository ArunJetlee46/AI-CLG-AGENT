import sys

from app.services.admin import ai_tools as _module

sys.modules[__name__] = _module
