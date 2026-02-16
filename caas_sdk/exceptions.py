"""
CAAS SDK Exceptions
"""


class CAASError(Exception):
    """Base exception for CAAS SDK"""



class AuthenticationError(CAASError):
    """Authentication failed"""



class RateLimitError(CAASError):
    """Rate limit exceeded"""

    def __init__(self, message: str, retry_after: int = 0):
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(CAASError):
    """Validation error"""



class APIError(CAASError):
    """API request error"""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class TimeoutError(CAASError):
    """Request timeout"""



class NetworkError(CAASError):
    """Network error"""

