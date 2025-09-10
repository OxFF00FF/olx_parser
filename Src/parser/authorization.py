import os
import time

import undetected_chromedriver as uc
from playwright.sync_api import sync_playwright

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.parser.utils import save_json, open_json


def get_session_id(user_dir='guest') -> str | None:
    """
    Получает ID Сесии аккаунта после входа или возвращет уже существующий, используя указанный профиль браузера.

    :param user_dir: Имя директории с пользовательским профилем Chrome (по умолчанию 'guest').
    """
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    os.makedirs(data_dir, exist_ok=True)

    auth_file = os.path.join(data_dir, 'common', 'authorize.json')

    chrome_dir = os.path.join(os.path.dirname(data_dir), 'chrome')
    user_dir = os.path.join(chrome_dir, 'profiles', user_dir)
    chrome_path = os.path.join(chrome_dir, 'chrome-win64', 'chrome.exe')
    driver_path = os.path.join(chrome_dir, 'driver-win64', 'chromedriver.exe')
    user_dir_existed = os.path.exists(user_dir)

    if not user_dir_existed:
        print(f"\n‼️  {LIGHT_YELLOW}Папка пользователя не найдена{WHITE} · Сейчас откроется браузер, вам нужно войти в свой аккаунт OLX в течении минуты и дождаться когда браузер закроется")
        if os.path.exists(auth_file):
            os.remove(auth_file)
        time.sleep(5)

    chrome_options = uc.ChromeOptions()
    if user_dir_existed:
        chrome_options.add_argument("--headless")

    chrome_options.add_argument(f"--user-data-dir={user_dir}")
    chrome_options.add_argument("--disable-notifications")
    driver = None

    try:
        if not os.path.exists(auth_file):
            print(f"‼️  {LIGHT_YELLOW}Файл {WHITE}`authorize.json`{LIGHT_YELLOW} не найден{WHITE} · Получаем новый Идентификатор сессии")

            # driver = uc.Chrome(options=chrome_options)
            driver = uc.Chrome(options=chrome_options, browser_executable_path=chrome_path, driver_executable_path=driver_path)
            driver.implicitly_wait(60)

            logger.info(f"⚙️  [{DARK_GRAY}Profile: {BOLD}{user_dir}{RESET}{WHITE}]")
            logger.info(f"⚙️  [{DARK_GRAY}Chrome:  {BOLD}{chrome_path}{RESET}{WHITE}]")
            logger.info(f"⚙️  [{DARK_GRAY}Driver:  {BOLD}{driver_path}{RESET}{WHITE}]")
            logger.info(f"⚙️  [{DARK_GRAY}Version: {BOLD}{driver.capabilities.get('chrome', {}).get('chromedriverVersion')}{RESET}{WHITE}]")
            time.sleep(3)

            driver.get('https://www.olx.ua/uk/myaccount/settings')
            logger.info(f"⚙️  {driver.current_url}")

            if not user_dir_existed:
                driver.maximize_window()
                time.sleep(60)

            if not os.path.exists(auth_file):
                driver.maximize_window()
                time.sleep(30)

            if driver.title == 'OLX.UA - Увійти':
                logger.error(f"❌  {LIGHT_RED}Не удалось получить токен{WHITE} · Попробуйтн снова (Возможно сработала капча или вы не успели войти в аккаунт)")
                return None
            else:
                if 'satisfied' in driver.title:
                    logger.error(f"Сработала блокировка CloudFront. Попробуйте позже")
                    return None
                else:
                    logger.info(f"✔️  {driver.title}")

            driver.minimize_window()
            time.sleep(5)

            cookies = driver.execute_cdp_cmd("Network.getAllCookies", {}).get('cookies', [])
            session_id = next((cookie['value'] for cookie in cookies if cookie['name'] == 'SID' and cookie['domain'] == 'login.olx.ua'), None)
            if session_id:
                save_json(dict(login_sid=session_id), auth_file)
                print(f"\n✔️  {LIGHT_GREEN}SID получен{WHITE} · {session_id}")
                return session_id

            print(f"❌  Не удалось получить идентификатор сесии · {session_id=}")
            return None

        else:
            session_id = open_json(auth_file).get('login_sid')
            if session_id:
                logger.debug(f"✔️  {LIGHT_GREEN}Текущий SID{WHITE} · {session_id}")
                return session_id
            else:
                print(f"❌  Не удалось найти идентификатор сесии в файле · {auth_file}\n")
                return None

    finally:
        if driver:
            driver.close()


def get_session_id_pw(user_dir: str = "guest") -> str | None:
    """
    Получает ID сессии аккаунта OLX после входа или возвращает уже существующий,
    используя указанный профиль браузера (Playwright sync).

    :param user_dir: Имя директории с пользовательским профилем Chrome (по умолчанию 'guest').
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    auth_file = os.path.join(data_dir, "common", "authorize.json")

    chrome_dir = os.path.join(os.path.dirname(data_dir), "chrome")
    user_data_dir = os.path.join(chrome_dir, "profiles", user_dir)
    user_dir_existed = os.path.exists(user_data_dir)

    if not user_dir_existed:
        print(f"\n‼️  Папка пользователя не найдена · Сейчас откроется браузер, войдите в аккаунт OLX в течение минуты и дождитесь закрытия браузера")
        if os.path.exists(auth_file):
            os.remove(auth_file)
        time.sleep(5)

    if os.path.exists(auth_file):
        session_id = open_json(auth_file).get("login_sid")
        if session_id:
            print(f"✔️  Текущий SID · {session_id}")
            return session_id

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=user_dir_existed,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        )

        logger.info(f"⚙️  [{DARK_GRAY}Profile: {BOLD}{user_data_dir}{RESET}{WHITE}]")
        logger.info(f"⚙️  [{DARK_GRAY}Chrome:  {BOLD}{p.chromium.executable_path}{RESET}{WHITE}]")
        logger.info(f"⚙️  [{DARK_GRAY}Version: {BOLD}{browser.browser.version}{RESET}{WHITE}]")
        time.sleep(3)

        page = browser.new_page()
        page.goto("https://www.olx.ua/uk/myaccount/settings")

        if not user_dir_existed:
            time.sleep(60)

        if not os.path.exists(auth_file):
            time.sleep(30)

        if "Увійти" in page.title():
            print("❌  Не удалось получить токен · Возможно сработала капча или вы не успели войти")
            browser.close()
            return None
        elif "satisfied" in page.title().lower():
            print("❌  Сработала блокировка CloudFront. Попробуйте позже")
            browser.close()
            return None
        else:
            print(f"✔️  {page.title()}")

        cookies = browser.cookies()
        session_id = next((cookie["value"] for cookie in cookies if cookie["name"] == "SID" and "login.olx.ua" in cookie["domain"]), None)

        if session_id:
            save_json({"login_sid": session_id}, auth_file)
            print(f"\n✔️  SID получен · {session_id}")
            browser.close()
            return session_id
        else:
            print("❌  Не удалось получить идентификатор сессии")
            browser.close()
            return None
