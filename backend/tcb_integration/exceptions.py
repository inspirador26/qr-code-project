class TcbError(RuntimeError):
    """Base for anything that goes wrong talking to (or standing in for) TCB."""


class TcbConfigError(TcbError):
    """Raised when required TCB credentials/settings are missing."""


class TcbApiError(TcbError):
    """Raised for a non-2xx TCB response that isn't a modeled partial-failure
    bucket (see client.DepositResult) — i.e. something actually went wrong
    with the call itself, not with individual items in a batch.
    """

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}
