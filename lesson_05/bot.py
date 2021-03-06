# -*- coding: utf-8 -*-

import time
import eventlet
import requests
import logging
import telebot
from time import sleep

# Каждый раз получаем по 10 последних записей со стены
URL_VK = 'https://api.vk.com/method/wall.get?domain=c.music&count=10&filter=owner'
FILENAME_VK = 'last_known_id.txt'
BASE_POST_URL = 'https://vk.com/wall-39270586_'

BOT_TOKEN = 'токен бота, постящего в канал'
CHANNEL_NAME = '@канал'

# Если True, предполагается использование cron для запуска скрипта
# Если False, процесс запускается и постоянно висит запущенный
SINGLE_RUN = False

bot = telebot.TeleBot(BOT_TOKEN)


def get_data():
    timeout = eventlet.Timeout(10)
    try:
        feed = requests.get(URL_VK)
        return feed.json()
    except eventlet.timeout.Timeout:
        logging.warning('Got Timeout while retrieving VK JSON data. Cancelling...')
        return None
    finally:
        timeout.cancel()


def check_new_posts_vk():
    # Пишем текущее время начала
    logging.info('[VK] Started scanning for new posts')
    with open(FILENAME_VK, 'rt') as file:
        last_id = int(file.read())
        logging.info('Last ID (VK) = {!s}'.format(last_id))
    try:
        feed = get_data()
        # Если ранее случился таймаут, пропускаем итерацию. Если всё нормально - парсим посты.
        if feed is not None:
            entries = feed['response']
            # 0 - это какое-то число, так что начинаем с 1
            for i in range(1, len(entries)):
                # Дошли до прошлого результата - останавливаемся
                if entries[i]['id'] <= last_id:
                    break
                try:
                    # Если пост был закреплен, пропускаем его
                    tmp = entries[i]['is_pinned']
                    continue
                # Формируем ссылку на пост в группе и отправляем
                except KeyError:
                    link = '{!s}{!s}'.format(BASE_POST_URL, entries[i]['id'])
                    bot.send_message(CHANNEL_NAME, link)
                    # Спим одну секунду, чтобы Телеграм не отругал нас за частые обращения к серверу
                    sleep(1)
                    # Записываем новую "верхушку" группы, чтобы не повторяться
            with open(FILENAME_VK, 'wt') as file:
                try:
                    tmp = entries[1]['is_pinned']
                    # Если первый пост - закрепленный, то сохраняем ID второго
                    file.write(str(entries[2]['id']))
                    logging.info('New last_id (VK) is {!s}'.format((entries[2]['id'])))
                except KeyError:
                    file.write(str(entries[1]['id']))
                    logging.info('New last_id (VK) is {!s}'.format((entries[1]['id'])))
    except Exception as ex:
        logging.error('Exception of type {!s} in check_new_post(): {!s}'.format(type(ex).__name__, str(ex)))
        pass
    logging.info('[VK] Finished scanning')
    return


if __name__ == '__main__':
    # Избавляемся от спама в логах от библиотеки requests
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    # Настраиваем наш логгер
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO,
                        filename='bot_log.log', datefmt='%d.%m.%Y %H:%M:%S')
    if not SINGLE_RUN:
        while True:
            check_new_posts_vk()
            # Пауза в 4 минуты перед повторной проверкой
            logging.info('[App] Script went to sleep.')
            time.sleep(60 * 4)
    else:
        check_new_posts_vk()
    logging.info('[App] Script exited.\n')
