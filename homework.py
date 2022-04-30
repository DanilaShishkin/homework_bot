import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import CheckHomeworks

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s, %(levelname)s, %(message)s"
                    )
logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info('Отправка сообщения ' + message)
        check = True
    except Exception as error:
        logger.critical(f'Сбой при отправке сообщения в Telegram: {error}')
        check = False
    return check


def get_api_answer(current_timestamp):
    """Запрос статуса проверки ЯП."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        message = 'ошибка запроса'
    if response.status_code != HTTPStatus.OK:
        message = f'ошибочный статус ответа по API: {response.status_code}'
        raise CheckHomeworks(message)
    return response.json()


def check_response(response):
    """Проверка запроса."""
    if isinstance(response, dict) is False:
        message = 'Отсутствует словарь'
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'Не корректный словарь'
        raise CheckHomeworks(message)
    try:
        homeworks = response.get('homeworks')
    except CheckHomeworks:
        message = 'Отсутствует homeworks'
    if isinstance(homeworks, list) is False:
        message = 'Отсутствует словарь'
        raise TypeError(message)
    if not response['homeworks']:
        message = f'отсутствует ключ homeworks в ответе: {response}'
        raise CheckHomeworks(message)
    logger.info('Status of homework update')
    return homeworks[0]


def parse_status(homework):
    """Распаковка запроса."""
    if 'homework_name' not in homework:
        message = 'Нет ключа "homework_name" в ответе API'
        raise KeyError(message)
    if 'status' not in homework:
        message = 'Нет ключа "status" в ответе API'
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка TOKENS."""
    return (PRACTICUM_TOKEN is not None
            or TELEGRAM_TOKEN is not None
            or TELEGRAM_CHAT_ID is not None)


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Одна или более переменных окружения не определены')
        raise
    logger.info('Бот запущен')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response['homeworks']:
                homeworks = check_response(response)
                send_message(bot, parse_status(homeworks))
            current_timestamp = response['current_date']
        except CheckHomeworks as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if message != status and send_message(bot, message):
                status = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if message != status and send_message(bot, message):
                status = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
