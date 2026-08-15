import sys

from app.services.rag import graph_service as _module

sys.modules[__name__] = _module
