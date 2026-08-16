import sys

from app.services.students import growth as _module

sys.modules[__name__] = _module
