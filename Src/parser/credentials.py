import datetime
import json
import os

from curl_cffi import requests
from yarl import URL

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.parser.authorization import get_session_id
from Src.parser.utils import save_json, open_json


def save_token(token_data: dict, updated=None):
    seconds = token_data.get('expires_in')
    minutes = seconds // 60
    expire_date = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    expire_ts = int(expire_date.timestamp())
    formatted_time = expire_date.strftime('%H:%M:%S')

    token_data.update(dict(
        relative=f'{minutes} мин.',
        timestamp=expire_ts,
        time=formatted_time,
        date=str(expire_date)
    ))

    action = 'обновлен' if updated else 'получен'
    print(f"\n⌛️  {LIGHT_GREEN}Токен {action}{WHITE} · Истекает через {LIGHT_YELLOW}{minutes} мин{WHITE} в {LIGHT_MAGENTA}{formatted_time}{WHITE}")

    creds_file = os.path.join(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data'), 'credentials.json')
    save_json(token_data, creds_file)


def get_auth_code(login_sid: str) -> str | None:
    cookies = {'SID': login_sid}
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'referer': 'https://www.olx.ua/',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'iframe',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    }
    params = {
        'client_id': '309lsgh0deirlo2la9kmrmhe3v',
        'scope': 'openid profile email offline_access',
        'redirect_uri': 'https://www.olx.ua/d/callback/',
        'prompt': 'none',
        'response_type': 'code',
        'response_mode': 'web_message',
        'code_challenge': 'EG3uvQhW7QJdT6fQWtQyKLlaeb-_MXWCBSuvP1yh8fU',
        'code_challenge_method': 'S256',
    }
    url = str(URL('https://login.olx.ua/oauth2/authorize').with_query(params))

    try:
        response = requests.get(url, headers=headers, cookies=cookies, impersonate='chrome')
        status = response.status_code

        if status == 200:
            cookies = dict(response.cookies)
            if 'SID' in cookies:
                logger.debug(f"ℹ️  Account status: {cookies}")
                match = re.search(r'authorizationResponse = (.*?);', string=response.text)
                authotization_code = json.loads(match.group(1)).get('response', {}).get('code')

                if not authotization_code:
                    logger.error(f"⚠️  Не удалось найти код авторизации")
                    return None

                logger.debug(f"✔️  {LIGHT_GREEN}Код авторизации{WHITE} · {authotization_code}")
                return authotization_code

            else:
                logger.error(f"⚠️  Accaunt unlogged: {cookies}")

        else:
            logger.error(f"⚠️  Failed to get authorization code · {status} {response.text}")

    except Exception as e:
        logger.error(f"⚠️  Failed to get authorization code · {e}")


def update_token(refresh_token: str) -> str | None:
    headers = {
        'accept': '*/*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.olx.ua',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.olx.ua/',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    }
    payload = {
        'client_id': '309lsgh0deirlo2la9kmrmhe3v',
        'redirect_uri': 'https://www.olx.ua/d/callback/',
        'st': 'eyJzbCI6IjE5Nzk3YTcwNzYyeDUyYWI5NjNiIiwicyI6IjE5N2EwOWFlYzQweDRhYmQyYjE0In0=',
        'cc': 'eyJjYyI6MCwiZ3JvdXBzIjoiIn0=',
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }

    try:
        response = requests.post('https://login.olx.ua/oauth2/token', headers=headers, data=payload, impersonate='chrome')
        status = response.status_code
        data = response.json()

        if status == 200:
            save_token(data, updated=True)
            logger.debug("✅  Acces token updated by refresh token")
            return data.get('access_token')
        else:
            logger.error(f"⚠️  Failed to update token with provided refresh token")
            return None

    except Exception as e:
        logger.error(f"❌  Failed to update token · {e}")


def get_access_token(authorization_code: str) -> str | None:
    headers = {
        'accept': '*/*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.olx.ua',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.olx.ua/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }
    payload = {
        'client_id': '309lsgh0deirlo2la9kmrmhe3v',
        'redirect_uri': 'https://www.olx.ua/d/callback/',
        'st': 'eyJzbCI6IjE5Nzk3YTcwNzYyeDUyYWI5NjNiIiwicyI6IjE5N2EwOWFlYzQweDRhYmQyYjE0In0=',
        'cc': 'eyJjYyI6MCwiZ3JvdXBzIjoiIn0=',
        'code_verifier': 'TMZFBsH5ApbNaG6.He8uKJkwaEU.mZX8VJeTLJqQr5s',
        'code': authorization_code,
        'grant_type': 'authorization_code',
    }

    try:
        response = requests.post('https://login.olx.ua/oauth2/token', headers=headers, data=payload, impersonate='chrome')
        status = response.status_code
        data = response.json()

        if status == 200:
            save_token(data)
            logger.debug("✅  Access token recieved")
            return data.get('access_token')
        else:
            logger.error(f"⚠️  Failed to get acces token with provided auth_code · {data}")

    except Exception as e:
        logger.error(f"⚠️  Failed to get access token · {e}")


def get_token(user='guest', show_info=None) -> str | None:
    """
    Получает токен доступа для OLX, используя указанный профиль браузера.

    Если папка пользователя не найдена, то пытаемся получить SID через браузер и сохраняем в файл,
    Зачем с ним получаем код авторизации и после этого с кодом получаем access_token и сохраняем в файл

    Если файл уже есть, то проверяем не истекло ли время действия, если истекло то обновляем через refresh_token
    Если файла нет, то делаем повторно авторизацию для получения SID и кода доступа

    :return: Строка токена в формате "Bearer ..." или None, если получение не удалось.
    """
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    creds_file = os.path.join(data_dir, 'credentials.json')
    user_dir = os.path.join(os.path.dirname(data_dir), 'chrome', 'profiles', user)
    user_dir_existed = os.path.exists(user_dir)

    if not user_dir_existed:
        get_access_token(get_auth_code(login_sid=get_session_id()))

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

            token = data.get('access_token')
            if show_info:
                print(f"\n⌛️  Время действия токена: {LIGHT_MAGENTA}{formatted_time}{WHITE}")
                return
            else:
                return token

        else:
            print(f"\n⚠️  {YELLOW}Время действия токена истекло{WHITE} · Обновляем")
            token = update_token(data.get('refresh_token'))
            if not token:
                token = get_access_token(get_auth_code(login_sid=get_session_id()))

    else:
        print(f"\n⚠️  {YELLOW}Файл с токеном не найден{WHITE} · Получаем новый")
        token = get_access_token(get_auth_code(login_sid=get_session_id()))

    if token:
        return f"Bearer {token}"
