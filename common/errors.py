class TransientError(Exception):
    """Retryable failure: network blips, rate limits, timeouts."""


class PermanentError(Exception):
    """Non-retryable failure: invalid input, policy violation, malformed output."""


class ValidationError(PermanentError):
    """Agent output failed schema validation."""
