import sys

from app.services.rag import vector_store as _module

sys.modules[__name__] = _module
