class HomeworkStatus(Exception):
    """Исключение при не корректном словаре homework."""

    pass


class CheckResponseStatus(Exception):
    """Ошибка при ответе по API."""

    pass


class HomeworksNotExist(Exception):
    """Исключение отсутствует homeworks."""

    pass
