import sys

from app.services.rag import curriculum as _module

sys.modules[__name__] = _module
