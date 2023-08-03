import os
import logging
import time
import sys
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv

from .exceptions import APIResponseError, APIRequestError

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

RETRY_PERIOD = 600  # 10 минут
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия всех токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        logging.debug(f'Отправляем сообщение в телеграм: {message}')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except telegram.error.TelegramError:
        logging.error('Ошибка отправки сообщения в Telegram.')
    else:
        logging.info('Телеграм сообщение отправлено.')


def get_api_answer(timestamp):
    """Получение ответа от API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as error:
        message = f'Ошибка в запросе к API: {error}'
        raise APIRequestError(message)
    if response.status_code != HTTPStatus.OK:
        raise APIResponseError('API вернула код, не соответствующий 200')
    return response.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    logging.info(
        'Приступаю к проверке ответа от API.'
    )
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API.')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Пустой ответ от API.')
    if not isinstance(response['current_date'], int):
        raise TypeError('"Current_date" не является числом.')
    if not isinstance(response['homeworks'], list):
        raise TypeError('"Homeworks" не является списком.')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError(
            'В домашней работе в ответе от API отсутствует ключ'
            f' "homework_name" : homework = {homework}.'
        )
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(
            'В ответе от API пришел неизвестный статус работы,'
            f' status = {homework_status}.'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}".{verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют необходимые токены для работы программы.'
        logging.critical(message)
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_report = ''

    while True:
        try:
            new_request = get_api_answer(timestamp)
            check_response(new_request)
            logging.info('Запрос API прошел проверку.')
            homeworks = new_request['homeworks']
            if not homeworks:
                logging.info('Нет активной работы.')
                continue
            homework = parse_status(homeworks[0])
            if homework != current_report:
                send_message(bot, homework)
                logging.info(f'Отправлен новый статус: {homework}')
                current_report = new_request
                timestamp = new_request.get('current_date')
            else:
                logging.info('Статус не изменился.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message
            )

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            '%(asctime)s, [%(levelname)s] -'
            '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
        ),
        handlers=[
            logging.FileHandler(f'{BASE_DIR}/output.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
