import sys

from app.services.admin import copilot as _module

sys.modules[__name__] = _module
