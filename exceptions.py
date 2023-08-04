class APIRequestError(Exception):
    """Ошибка в запросе к API."""


class APIResponseError(Exception):
    """Ответ API не соответсвует коду 200."""
