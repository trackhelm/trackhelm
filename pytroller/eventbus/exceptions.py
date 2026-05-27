class EventBusError(Exception):
    """Base event bus exception."""


class EventHandlerError(EventBusError):
    """Raised when an event handler fails."""
