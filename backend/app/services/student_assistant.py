import sys

from app.services.students import assistant as _module

sys.modules[__name__] = _module
