from curl_cffi import AsyncSession
from curl_cffi.requests.exceptions import DNSError

from Src.app.config import app_config
from Src.app.logging_config import logger
from Src.parser.utils import get_proxy_random


async def get_data(
        url,
        headers=None,
        cookies=None,
        params=None,
        payload=None,
        data=None,
        Json=None,
        use_proxy=None,
        proxy=None,
) -> tuple[int, dict | str]:
    """
    Получает данные с указанного URL, выполняя запрос с поддержкой прокси и опций отладки.

    :param url: URL-адрес для выполнения HTTP-запроса.
    :param headers: Заголовки запроса.
    :param cookies: Куки.
    :param params: Параметры запроса.
    :param payload: JSON-данные для POST-запроса.
    :param data: Данные формы или строка.
    :param Json: Вернуть результат как JSON (True) или текст (False)..
    :param use_proxy: Использовать ли прокси.
    :param proxy: Конкретный прокси.
    :return: Кортеж из текста/JSON и статуса ответа.
    """
    # from curl_cffi.requests.impersonate import BrowserTypeLiteral
    proxy = proxy or get_proxy_random()

    request_args = {
        'url': url,
        'headers': headers,
        'cookies': cookies,
        'params': params,
        'timeout': 10,
        'impersonate': 'chrome',
        'verify': False
        # 'allow_redirects': True
    }

    method = 'post' if data or payload else 'get'
    if method == 'post':
        if data:
            request_args['data'] = data
        elif payload:
            request_args['json'] = payload

    if use_proxy is None:
        use_proxy = app_config.USE_PROXY

    if use_proxy:
        request_args['proxy'] = proxy
        logger.debug(f"🌐  Using proxy: {proxy}")

    try:
        logger.debug(f"{'🔵  ' if method == 'get' else '🟠  '}{method.upper()} · {url}")

        async with AsyncSession() as session:
            response = await session.get(**request_args) if method == 'get' else await session.post(**request_args)
            status = response.status_code

            if Json:
                try:
                    return status, response.json()
                except Exception:
                    return status, response.text
            else:
                return status, response.text

    except DNSError as e:
        logger.error(f'🌐  Не удалось выполнить запрос, проверьте подключение к интернету · {e}')
        return 500, f"{type(e).__name__}. {e}"

    except Exception as e:
        return 500, f"{proxy} · {type(e).__name__}. {e}"
