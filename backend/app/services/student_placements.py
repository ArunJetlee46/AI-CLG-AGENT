import sys

from app.services.students import placements as _module

sys.modules[__name__] = _module
