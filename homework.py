import requests

import logging

import sys

import time

import os

import telegram

from dotenv import load_dotenv

from http import HTTPStatus

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


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


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Удачная отправка сообщения')
    except Exception:
        logging.error('Неудачная отправка сообщения')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    status = response.status_code
    if status == HTTPStatus.OK:
        return response.json()
    else:
        message = 'Сбой в работе программы: Эндпоинт ',
        'https://practicum.yandex.ru/api/user_api/homework_statuses/ ',
        f'недоступен. Код ответа API: {status}'
        logging.error(message)
        raise TypeError(message)


def check_response(response):
    """Проверяет ответ API на корректность."""
    if ('homeworks' in response) and (type(response.get('homeworks')) is list):
        return response.get('homeworks')
    else:
        message = 'Отсутствуют ожидаемые ключи в ответе API.'
        logging.error(message)
        raise TypeError(message)


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not (homework_status in HOMEWORK_STATUSES):
        message = 'Недокументированный статус домашней работы, ',
        'обнаруженный в ответе API.'
        logging.error(message)
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            if not check_tokens():
                message = 'Отсутствуют переменные окружения'
                logging.critical(message)
                raise TypeError(message)
            response = check_response(get_api_answer(current_timestamp))

            if len(response) > 0:
                for homework in response:
                    message = parse_status(homework)
                    send_message(bot, message)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
