class ScrybeError(Exception):
    """Base SCRYBE exception."""


class FetchError(ScrybeError):
    """Raised when a source cannot be fetched."""


class ParserError(ScrybeError):
    """Raised when content cannot be parsed."""


class ExternalDependencyUnavailable(ScrybeError):
    """Raised when an optional runtime is not installed."""

