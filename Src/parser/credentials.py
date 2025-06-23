import datetime
import os
import time

import undetected_chromedriver as uc

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.parser.utils import save_json, open_json


def get_token(user_dir='guest', show_info=None) -> str | None:
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    user_dir = os.path.join(data_dir, 'profiles', user_dir)
    creds_file = os.path.join(data_dir, 'credentials.json')
    user_dir_existed = os.path.exists(user_dir)

    if not user_dir_existed:
        print("ℹ️  Папка пользователя не найдена. Сейчас откроется браузер, вам нужно войти в свой аккаунт OLX в течении минуты и дождаться когда браузер закроется")
        time.sleep(10)

    chrome_options = uc.ChromeOptions()
    if user_dir_existed:
        chrome_options.add_argument("--headless")

    chrome_options.add_argument(f"--user-data-dir={user_dir}")
    chrome_options.add_argument("--disable-notifications")
    driver = None

    try:
        # Проверяем есть ли файл с токеном
        if os.path.exists(creds_file):
            data = open_json(creds_file)
            expire_ts = int(data.get('expires_in'))
            now_ts = int(datetime.datetime.now().timestamp())

            if expire_ts and now_ts < expire_ts:
                remaining = int(expire_ts - now_ts)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                formatted_time = f'{hours:02}:{minutes:02}:{seconds:02}'

                if show_info:
                    print(f"\n⌛️  Время действия токена: {LIGHT_MAGENTA}{formatted_time}{WHITE}")

                return data.get('token')
            else:
                print(f"⚠️  {YELLOW}Время действия токена истекло{WHITE} · Получаем новый \n")
                time.sleep(2)
        else:
            print(f"⚠️  {YELLOW}Файл с токеном не найден{WHITE} · Получаем новый \n")
            time.sleep(2)

        # Если файла нет илитоен истек, то создаем и запускаем драйвер
        # logger.info(f"⚙️  {DARK_GRAY}[Profile: {user_dir}]{WHITE}")

        driver = uc.Chrome(options=chrome_options)
        driver.implicitly_wait(60)

        driver.get('https://www.olx.ua/myaccount/')

        if not user_dir_existed:
            logger.info(f"ℹ️  {driver.title}")
            time.sleep(60)

        access_token = next((cookie['value'] for cookie in driver.get_cookies() if cookie['name'] == 'access_token'), None)
        token = f"Bearer {access_token}"

        if not access_token:
            print(f"⚠️  Не удалось получить токен · {access_token=}")
            return None

        seconds = 900
        minutes = seconds // 60
        expire_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        expire_ts = int(expire_time.timestamp())
        formatted_time = expire_time.strftime('%H:%M:%S')

        save_json(dict(token=token, expires_in=expire_ts, expires_str=formatted_time), creds_file)
        print(f"⌛️  {LIGHT_GREEN}Токен получен{WHITE} · Истекает через {LIGHT_YELLOW}{minutes} мин{WHITE} в {LIGHT_MAGENTA}{formatted_time}{WHITE}")

        return token

    finally:
        if driver:
            driver.close()
