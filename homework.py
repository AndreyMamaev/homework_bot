import sys
import time
import logging
from http import HTTPStatus

import telegram
import requests

from config import (
    PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    RETRY_TIME, ENDPOINT, HEADERS, HOMEWORK_STATUSES
)
from exception import (
    SendMessageError, ApiAnswerError, CheckResponseError,
    HomeworkStatusError, CheckTokensError
)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Удачная отправка сообщения')
    except telegram.error.BadRequest:
        message = 'Неудачная отправка сообщения'
        logging.error(message)
        raise SendMessageError(message)


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    status = response.status_code
    if status == HTTPStatus.OK:
        return response.json()
    message = f'Сбой в работе программы: Эндпоинт {ENDPOINT} ',
    f'недоступен. Код ответа API: {status}'
    logging.error(message)
    raise ApiAnswerError(message)


def check_response(response):
    """Проверяет ответ API на корректность."""
    if (isinstance(response, dict)) and (
        isinstance(response.get('homeworks'), list)
    ):
        return response.get('homeworks')
    else:
        message = 'Отсутствуют ожидаемые ключи в ответе API.'
        logging.error(message)
        raise CheckResponseError(message)


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if (homework_name and homework_status) is None:
        raise KeyError(
            'Отсутствует информация о названии или статусе работы'
        )

    if homework_status not in HOMEWORK_STATUSES:
        message = 'Недокументированный статус домашней работы, ',
        'обнаруженный в ответе API.'
        logging.error(message)
        raise HomeworkStatusError(message)
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
                raise CheckTokensError(message)
            answer = get_api_answer(current_timestamp)
            response = check_response(answer)

            if len(response) > 0:
                for homework in response:
                    message = parse_status(homework)
                    send_message(bot, message)

            current_timestamp = answer.get("current_date")

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    main()
