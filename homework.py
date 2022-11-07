import datetime
import logging
import os
import requests
import telegram
import time
from dotenv import load_dotenv


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


class ErrorStatus(Exception):
    """Проект еще не взят на проверку."""


class StatusCodeIsNot200(Exception):
    """Код ответа страницы не равен 200."""


def send_message(bot, message):
    """Отправка сообщения в Телеграм-канал."""
    logger.info('Попытка отправить сообщение.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            f'Следующее сообщение было отправлено в Телеграм-канал: {message}'
        )
    except Exception as error:
        error_message = f'Сообщение в Телеграм-канал не отправлено: {error}'
        logger.error(error_message)
        bot.send_message(TELEGRAM_CHAT_ID, error_message)


def get_api_answer(current_timestamp):
    """Отправка запроса к API-сервису и получение запрошенных данных."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        error_message = (
            f'Сервис ЯП {ENDPOINT} недоступен.'
            f'Код ответа API: {response.status_code}')
        logger.error(error_message)
        raise StatusCodeIsNot200(error_message)
    return response.json()


def check_response(response):
    """Проверяем ответа API на корректность."""
    if response['homeworks'] is None:
        logger.error('Ошибка в полученных данных при запросе.')
    if response['homeworks'] == []:
        return {}
    return response['homeworks'][0]


def parse_status(homework):
    """Извлечение из информации о конкретной работе статуса этой работы."""

    if 'homework_name' not in homework:
        error_message = 'Ошибка доступа по ключу "homework_name".'
        logger.error(error_message)
        raise KeyError(error_message)
    if 'status' not in homework:
        error_message = 'Ошибка доступа по ключу "status".'
        logger.error(error_message)
        raise KeyError(error_message)

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        error_message = 'Статус проекта незадокументирован.'
        logger.error(error_message)
        raise ErrorStatus(error_message)

    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID,
    }
    for key, value in tokens.items():
        if value is None:
            logger.critical(f'{key} отсутствует.')
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменная окружения.')

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
            while quantity_of_homeworks > 0:
                message = parse_status(homeworks[quantity_of_homeworks - 1])
                send_message(bot, message)
                quantity_of_homeworks -= 1
            logger.debug(
                'Статус проекта не изменился. '
                'Повторный запрос будет отправлен через 10 минут.'
            )
            time.sleep(RETRY_TIME)

        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logger.error(error_message)
            send_message(bot, error_message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
