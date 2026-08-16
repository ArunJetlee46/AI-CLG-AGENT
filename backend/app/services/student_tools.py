import sys

from app.services.students import tools as _module

sys.modules[__name__] = _module
