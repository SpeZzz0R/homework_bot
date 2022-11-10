class ErrorStatus(Exception):
    """Проект еще не взят на проверку."""
    pass


class NoSendMessage(Exception):
    """Сообщение в Телеграм не отправлено."""
    pass


class RepeatMessage(Exception):
    """Было отправлено повторное сообщение."""
    pass


class RequestFailure(Exception):
    """Проищошел сбой при запросе к сервису."""
    pass


class StatusCodeIsNotOK(Exception):
    """Код ответа страницы не равен 200."""
    pass
