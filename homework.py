import logging
import os
import requests
import telegram
import time


from exceptions import HomeworkStatus, CheckResponseStatus, HomeworksNotExist
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 6
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
CHECK_MESSAGE = False

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s, %(levelname)s, %(message)s"
                    )


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logging.info('Отправка сообщения ' + message)
    except Exception as error:
        logging.critical(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Запрос статуса проверки ЯП."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        message = 'ошибка запроса'
        logging.error(message)
    if response.status_code != 200:
        message = f'ошибочный статус ответа по API: {response.status_code}'
        logging.error(message)
        raise CheckResponseStatus(message)
    return response.json()


def check_response(response):
    """Проверка запроса."""
    if type(response) != dict:
        message = 'Отсутствует словарь'
        logging.error(message)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'Не корректный словарь'
        logging.error(message)
        raise HomeworkStatus(message)
    try:
        homeworks = response.get('homeworks')
    except HomeworksNotExist:
        message = 'Отсутствует homeworks'
        logging.error(message)
    if type(homeworks) != list:
        message = 'Отсутствует словарь'
        logging.error(message)
        raise TypeError(message)
    if not response['homeworks']:
        message = f'отсутствует ключ homeworks в ответе: {response}'
        logging.error(message)
        raise HomeworkStatus(message)
    logging.info('Status of homework update')
    return homeworks[0]


def parse_status(homework):
    """Распаковка запроса."""
    if 'homework_name' not in homework:
        message = 'Нет ключа "homework_name" в ответе API'
        logging.error(message)
        raise KeyError('Нет ключа "homework_name" в ответе API')
    if 'status' not in homework:
        message = 'Нет ключа "status" в ответе API'
        logging.error(message)
        raise KeyError('Нет ключа "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка TOKENS."""
    if (PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
            or TELEGRAM_CHAT_ID is None):
        return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Одна или более переменных окружения не определены')
        raise
    logging.info('Бот запущен')
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
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            if message != status:
                send_message(bot, message)
                status = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
