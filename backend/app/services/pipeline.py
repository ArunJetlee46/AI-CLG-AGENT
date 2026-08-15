import sys

from app.services.rag import pipeline as _module

sys.modules[__name__] = _module
