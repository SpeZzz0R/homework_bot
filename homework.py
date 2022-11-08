import datetime
import exceptions
import logging
import os
import requests
import sys
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='info.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s',
)

logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    logger.info('Начало отправки сообщения в Телеграм.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            f'Следующее сообщение было отправлено в Телеграм: {message}'
        )
    except Exception as error:
        raise exceptions.NoSendMessage(
            f'Сообщение в Телеграм не отправлено: {error}'
        )


def get_api_answer(current_timestamp):
    """Отправка запроса к API-сервису и получение запрошенных данных."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise exceptions.RequestFailure(
            f'Проищошел сбой при запросе к сервису: {error}'
        )

    if response.status_code != HTTPStatus.OK:
        error_message = (
            f'Сервис ЯП {ENDPOINT} недоступен.'
            f'Код ответа API: {response.status_code}')
        raise exceptions.StatusCodeIsNotOK(error_message)
    return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Запрошенные данные - некорректны.')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise KeyError(
            'Отсутствует ключ "homeworks" в полученных данных от сервиса.'
        )
    if not isinstance(homeworks, list):
        raise TypeError(
            'Запрошенные данные - некорректны, в полученных данных должен '
            'быть список.'
        )
    return homeworks


def parse_status(homework):
    """Извлечение из информации о конкретной работе статуса этой работы."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError('Ошибка доступа по ключу "homework_name".')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise exceptions.ErrorStatus('Статус проекта незадокументирован.')

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    request_time = datetime.datetime.now()
    send_message(
        bot,
        f'Запрос сделан: {request_time.strftime("%d-%m-%Y %H:%M:%S")}'
    )

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            quantity_of_homeworks = len(homeworks)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                logger.info('Проектов нет.')
            while quantity_of_homeworks > 0:
                message = parse_status(homeworks[quantity_of_homeworks - 1])
                send_message(bot, message)
                quantity_of_homeworks -= 1
            logger.debug(
                'Статус проекта не изменился. '
                'Повторный запрос будет отправлен через 10 минут.'
            )

        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logger.error(error_message)
            send_message(bot, error_message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
