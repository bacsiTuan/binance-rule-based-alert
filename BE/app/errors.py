class BinanceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        retryable: bool = False,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after


class TelegramError(Exception):
    pass


class OpenAIClientError(Exception):
    pass


class CacheError(Exception):
    pass
