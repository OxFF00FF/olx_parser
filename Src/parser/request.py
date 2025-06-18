import asyncio

from curl_cffi import AsyncSession

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
        use_proxy=False,
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
    retries, max_retries, delay = 0, 5, 5
    proxy = proxy or get_proxy_random()

    request_args = {
        'url': url,
        'headers': headers,
        'cookies': cookies,
        'params': params,
        'timeout': 20,
        'impersonate': 'chrome110',
        'verify': False
        # 'allow_redirects': True
    }
    if app_config.DEBUG:
        logger.debug(f"Using proxy: {proxy}")

    if use_proxy:
        request_args['proxy'] = proxy

    method = 'post' if data or payload else 'get'
    if method == 'post':
        if data:
            request_args['data'] = data
        elif payload:
            request_args['json'] = payload

    while retries < max_retries:
        attempt = f"[Attempt {retries + 1}/{max_retries}]"
        try:
            async with AsyncSession() as session:
                response = await session.get(**request_args) if method == 'get' else await session.post(**request_args)
                status = response.status_code

                if app_config.DEBUG:
                    logger.debug(f"{method} · {response.url}")

                if Json:
                    try:
                        return status, response.json()
                    except Exception:
                        return status, response.text
                else:
                    return status, response.text

        except Exception as e:
            if app_config.DEBUG:
                logger.warning(f"{attempt} Error: {proxy} · {type(e).__name__}. {e}")

            retries += 1
            if retries < max_retries:
                await asyncio.sleep(delay)
            else:
                return 500, f"{proxy} · {type(e).__name__}. {e}"
