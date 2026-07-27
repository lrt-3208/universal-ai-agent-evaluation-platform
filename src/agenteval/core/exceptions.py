"""Exception hierarchy and error codes

Reference: ../contracts/error-model-contract.md §7
"""


class AgentEvalException(Exception):
    """Base exception for all AgentEval errors"""

    code: int = 50099
    http_status: int = 500
    retryable: bool = False
    message: str = "Internal error"
    detail: dict = {}

    def __init__(
        self,
        message: str | None = None,
        code: int | None = None,
        detail: dict | None = None,
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.detail = detail or {}
        super().__init__(self.message)


class ValidationError(AgentEvalException):
    """Field validation failure (400)"""

    code: int = 40000
    http_status: int = 400
    retryable: bool = False


class NotFoundException(AgentEvalException):
    """Resource not found (404)"""

    code: int = 40400
    http_status: int = 404
    retryable: bool = False


class ConflictException(AgentEvalException):
    """Unique constraint / state conflict (409)"""

    code: int = 40900
    http_status: int = 409
    retryable: bool = False


class ConfigurationError(AgentEvalException):
    """Adapter / Judge / Plugin config invalid (400)"""

    code: int = 40500
    http_status: int = 400
    retryable: bool = False


class TimeoutException(AgentEvalException):
    """Timeout error (retryable)"""

    code: int = 50500
    http_status: int = 504
    retryable: bool = True


class AdapterError(AgentEvalException):
    """Agent adapter call failure (retryable)"""

    code: int = 50502
    http_status: int = 502
    retryable: bool = True


class JudgeError(AgentEvalException):
    """Judge execution failure (retryable)"""

    code: int = 50600
    http_status: int = 502
    retryable: bool = True


class PluginLoadError(AgentEvalException):
    """Plugin load / init failure (500)"""

    code: int = 51001
    http_status: int = 500
    retryable: bool = False


class InternalError(AgentEvalException):
    """Uncategorized internal error (500)"""

    code: int = 50099
    http_status: int = 500
    retryable: bool = False


class DSLParseError(AgentEvalException):
    """DSL syntax parse failure (400)"""

    code: int = 40301
    http_status: int = 400
    retryable: bool = False
    message: str = "DSL parse error"


class DSLValidationError(AgentEvalException):
    """DSL validation failure (400)"""

    code: int = 40302
    http_status: int = 400
    retryable: bool = False
    message: str = "DSL validation failed"


class AdapterTimeoutError(AgentEvalException):
    """Agent adapter call timeout (retryable)"""

    code: int = 50501
    http_status: int = 504
    retryable: bool = True
    message: str = "Agent call timeout"


class UnsupportedAdapterError(AgentEvalException):
    """Unknown adapter type (400)"""

    code: int = 40502
    http_status: int = 400
    retryable: bool = False
    message: str = "Unsupported adapter type"


class InvalidAdapterConfigError(AgentEvalException):
    """Invalid adapter configuration (400)"""

    code: int = 40503
    http_status: int = 400
    retryable: bool = False
    message: str = "Invalid adapter config"


class EvaluationNotFoundError(NotFoundException):
    """Evaluation not found (404)"""

    code: int = 40405
    http_status: int = 404
    message: str = "Evaluation not found"


class DatasetEmptyError(AgentEvalException):
    """Dataset has no scenarios (400)"""

    code: int = 40501
    http_status: int = 400
    retryable: bool = False
    message: str = "Dataset has no scenarios"
