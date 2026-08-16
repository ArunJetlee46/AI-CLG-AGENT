import sys

from app.services.rag import llm as _module

sys.modules[__name__] = _module
