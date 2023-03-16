try:
    # Python 3.8+
    import importlib.metadata as importlib_metadata
except ImportError:
    # <Python 3.7 and lower
    import importlib_metadata

try:
    __version__ = importlib_metadata.version("django-push-notifications")
except Exception:
    __version = '3.0.0'
