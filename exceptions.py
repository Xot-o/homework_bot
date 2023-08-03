class APIRequestError(Exception):
    """Ошибка в запросе к API."""

    pass


class APIResponseError(Exception):
    """Ответ API не соответсвует коду 200."""

    pass
