import sys

from app.services.rag import evaluation as _module

sys.modules[__name__] = _module
