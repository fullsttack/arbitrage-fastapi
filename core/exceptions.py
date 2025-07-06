class ArbitrageException(Exception):
    """Base exception for arbitrage-related errors."""
    pass


class ExchangeException(Exception):
    """Base exception for exchange-related errors."""
    pass


class ExchangeAPIError(ExchangeException):
    """Exception raised when exchange API returns an error."""
    pass


class RateLimitError(ExchangeException):
    """Exception raised when rate limit is exceeded."""
    pass


class InsufficientBalanceError(ExchangeException):
    """Exception raised when user has insufficient balance."""
    pass


class OrderExecutionError(ExchangeException):
    """Exception raised when order execution fails."""
    pass


class InvalidTradingPairError(ExchangeException):
    """Exception raised for invalid trading pairs."""
    pass


class AuthenticationError(ExchangeException):
    """Exception raised for authentication failures."""
    pass


class ConfigurationError(ArbitrageException):
    """Exception raised for configuration issues."""
    pass


class ValidationError(ArbitrageException):
    """Exception raised for validation failures."""
    pass