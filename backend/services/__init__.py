"""Service package exports used by tests and runtime modules."""

from importlib import import_module


def __getattr__(name):
	if name == "socket_service":
		return import_module("services.socket_service")
	raise AttributeError(f"module 'services' has no attribute {name!r}")


