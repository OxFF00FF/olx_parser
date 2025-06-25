import datetime
import os
import time

import undetected_chromedriver as uc

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.parser.utils import save_json, open_json


def get_token(user_dir='guest', show_info=None) -> str | None:
    """
    Получает токен доступа для OLX, используя указанный профиль браузера.

    Если ранее сохранённый токен существует и ещё действителен — возвращает его.
    В противном случае запускает браузер (в headless если папка профиля уже существует),
    открывает страницу OLX для авторизации и извлекает токен из cookies.
    Новый токен сохраняется в `credentials.json` с меткой времени окончания действия.

    :param user_dir: Имя директории с пользовательским профилем Chrome (по умолчанию 'guest').
    :param show_info: Если установлен, выводит информацию о времени действия токена, но не возвращает сам токен.

    :return: Строка токена в формате "Bearer ..." или None, если получение не удалось.
    """
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    user_dir = os.path.join(data_dir, 'profiles', user_dir)
    creds_file = os.path.join(data_dir, 'credentials.json')
    user_dir_existed = os.path.exists(user_dir)

    if not user_dir_existed:
        print(f"\n‼️  {LIGHT_YELLOW}Папка пользователя не найдена{WHITE} · Сейчас откроется браузер, вам нужно войти в свой аккаунт OLX в течении минуты и дождаться когда браузер закроется")
        if os.path.exists(creds_file):
            os.remove(creds_file)
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
            expire_ts = int(data.get('timestamp'))
            now_ts = int(datetime.datetime.now().timestamp())

            if expire_ts and now_ts < expire_ts:
                remaining = int(expire_ts - now_ts)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                formatted_time = f'{hours:02}:{minutes:02}:{seconds:02}'

                if show_info:
                    print(f"\n⌛️  Время действия токена: {LIGHT_MAGENTA}{formatted_time}{WHITE}")
                    return
                return data.get('access_token')

            else:
                print(f"\n⚠️  {YELLOW}Время действия токена истекло{WHITE} · Получаем новый")
                time.sleep(2)

        else:
            print(f"\n⚠️  {YELLOW}Файл с токеном не найден{WHITE} · Получаем новый")
            time.sleep(2)

        # Если файла нет или токен истек, то создаем и запускаем драйвер
        # logger.info(f"⚙️  {DARK_GRAY}[Profile: {user_dir}]{WHITE}")

        driver = uc.Chrome(options=chrome_options)
        driver.implicitly_wait(60)

        driver.get('https://www.olx.ua/myaccount/settings')

        # Если нет папки профиля то ждем минуту, чтобы успеть войти в аккаунт
        if not user_dir_existed:
            driver.maximize_window()
            time.sleep(60)

        # Если нет файла с токеном то ждем 30 сек, чтобы успеть повторно войти
        if not os.path.exists(creds_file):
            time.sleep(30)

        driver.minimize_window()
        if driver.title == 'OLX.UA - Увійти':
            print(f"❌  {LIGHT_RED}Не удалось получить токен{WHITE} · Попробуйтн снова (Возможно сработала капча или вы не успели войти в аккаунт)")
            return None
        else:
            if 'satisfied' in driver.title:
                print(f"Сработала блокировка CloudFront. Попробуйте позже")
                return None
            else:
                print(f"✔️  {driver.title}")

        access_token = next((cookie['value'] for cookie in driver.get_cookies() if cookie['name'] == 'access_token'), None)

        if not access_token:
            print(f"⚠️  Не удалось получить токен · {access_token=}")
            return None

        seconds = 600
        minutes = seconds // 60
        expire_date = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        expire_ts = int(expire_date.timestamp())
        formatted_time = expire_date.strftime('%H:%M:%S')

        access_token = f"Bearer {access_token}"
        save_json(dict(access_token=access_token, timestamp=expire_ts, time=formatted_time, date=str(expire_date)), creds_file)
        print(f"\n⌛️  {LIGHT_GREEN}Токен получен{WHITE} · Истекает через {LIGHT_YELLOW}{minutes} мин{WHITE} в {LIGHT_MAGENTA}{formatted_time}{WHITE}")
        return access_token

    except Exception as e:
        logger.error(f"Ошибка во время работы драйвера · {e}")

    finally:
        if driver:
            driver.close()
