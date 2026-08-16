import importlib


def __getattr__(name: str):
    engine = importlib.import_module("app.services.rag.engine")
    return getattr(engine, name)
