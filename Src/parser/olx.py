import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime

from bs4 import BeautifulSoup as BS
from openpyxl import load_workbook
from tqdm.asyncio import tqdm_asyncio
from yarl import URL
from yaspin import yaspin

from Src.app.colors import *
from Src.app.config import app_config
from Src.app.logging_config import logger
from Src.parser.constants import limit
from Src.parser.request import get_data
from Src.parser.schemas import Context, Token, OfferID, Region, City, Category, OffersMeta, Offer
from Src.parser.utils import open_json, format_date, save_json
from Src.tables.olx import merge_city_offers, register_styles, save_offers


class olxParser:
    """
    Parser for OLX (https://www.olx.ua)

    API:

    - https://www.olx.ua/api/v1/offers/889972662/limited-phones/
    -
    """
    __base_url = 'https://www.olx.ua'
    __api_offers_url = f"{__base_url}/api/v1/offers"

    work_dir = os.path.join(os.path.dirname(__file__))
    data_dir = os.path.join(os.path.dirname(os.path.dirname(work_dir)), 'data')

    _cols = 150
    _bar = WHITE + '{desc} ' + LIGHT_BLUE + '| {bar} |' + LIGHT_YELLOW + ' {n_fmt}/{total_fmt} ' + DARK_GRAY + ' [Прошло: {elapsed}c · Осталось: {remaining}c · {rate_fmt}]  ' + WHITE
    _txt_all_offers = f"🔄  Парсим объявления со всех страниц  "

    def __init__(self, max_workers: int = 5, Json=None, Xlsx=None):
        self._workers = max_workers
        self._category_url = None

        self._save_json = Json
        self._save_xls = Xlsx

        self._semaphore = asyncio.Semaphore(self._workers)
        self._save_lock = asyncio.Lock()

        self.out_dir = os.path.join(self.data_dir)
        os.makedirs(self.out_dir, exist_ok=True)

    @staticmethod
    def _get_headers():
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ru',
            'content-type': 'application/json',
            'priority': 'u=1, i',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        }
        return headers

    @staticmethod
    def _get_cookies():
        cookies = {
            'lang': 'ru'
        }
        return cookies

    @staticmethod
    def _get_html(html_text: str) -> BS:
        try:
            return BS(html_text, 'html.parser')
        except Exception as e:
            raise e

    @staticmethod
    def _find_json(html: BS):
        script_text = next((item.get_text(strip=True) for item in html.find_all('script') if item.get('id') == 'olx-init-config'), None)
        if not script_text:
            logger.warning('`script_text` not found')
            return None

        match = re.search(r'window.__PRERENDERED_STATE__= (".*?");(?:\r\n|\r|\n)', script_text)
        if not match:
            logger.warning('`__PRERENDERED_STATE__` not found')
            return None

        return json.loads(json.loads(match.group(1)))

    async def _make_request(self, url, headers=None, data=None, payload=None, json_response=None, use_proxy=False) -> str | dict | None:
        """
        Делает запрос и проверяет статус ответа
        """
        logger.debug(url)
        if not url:
            logger.error(f'⚠️  Не удалось получить ответ для URL · {url}')
            return None

        headers = headers or self._get_headers()
        cookies = self._get_cookies()

        status, response = await get_data(url, headers, cookies, data, payload, Json=json_response, use_proxy=use_proxy)
        if status == 200:
            return response

        elif status == 404:
            logger.error("Объявление не найдено или удалено")
            return response if json_response else None

        elif status == 400:
            return response

        else:
            logger.error(f"⚠️  Unexpected status: {status}")
            html = self._get_html(response)
            logger.error(f"⚠️  {html.select_one('title').get_text()} · {url}")
            return {}

    @staticmethod
    def _format_offer(data: dict) -> Offer:
        offer = Offer()

        price_data = next((item.get('value') for item in data.get('params') if item.get('key') == 'price'), {})

        offer.id = data.get('id')
        offer.title = data.get('title')
        offer.seller_name = data.get('contact', {}).get('name')
        offer.seller_city = data.get('location', {}).get('city', {}).get('name')
        offer.description = data.get('description', '').replace('<br />', '\n').replace('<br/>', '\n').replace('<br>', '\n')

        price_label = price_data.get('label', '')
        if '$' in price_label:
            offer.price_usd = price_data.get('value')
            offer.price_uah = price_data.get('converted_value')
        elif 'грн' in price_label:
            offer.price_uah = price_data.get('value')
            offer.price_usd = price_data.get('converted_value')
        else:
            offer.price_usd = 'n/a'
            offer.price_uah = 'n/a'

        offer.price_str = price_data.get('label')
        offer.url = data.get('url')
        offer.posted_date = format_date(data.get('created_time'))

        offer.phone_number = str(data.get('contact', {}).get('phone'))

        return offer

    async def _pagination(self, category_url) -> int:
        logger.info(category_url)

        response = await self._make_request(category_url)

        html = self._get_html(response)

        script_text = next((item.get_text(strip=True) for item in html.find_all('script') if item.get('id') == 'olx-init-config'), None)
        match = re.search(r'window.__PRERENDERED_STATE__= (".*?");(?:\r\n|\r|\n)', script_text, re.DOTALL)
        if match:
            data = json.loads(json.loads(match.group(1)))
            return data.get('listing', {}).get('listing', {}).get('totalPages', 0)

    async def _get_offer_id(self, url: str) -> OfferID:
        """
        Получает и возвращает ID объявления из переданной ссылки
         - Ссылка объявление https://www.olx.ua/d/uk/obyavlenie/vdeokarta-pny-geforce-rtx-4060-ti-8gb-verto-vcg4060t8dfxpb1-o-IDWYtNQ.html

        :param url: Ссылка
        :return: Возвращает ID Объявления
        """
        response = await self._make_request(url)

        html = self._get_html(response)
        script_text = next((item.get_text(strip=True) for item in html.find_all('script') if '@type' in item.text), None)

        try:
            data = json.loads(script_text)
            ad_id = data.get('sku')
            return OfferID(value=ad_id)
        except Exception as e:
            logger.error(f"Failed to get ad_id. Error: {e} · {url}")

    async def _get_offer_data(self, ad_id: OfferID):
        url = f'{self.__api_offers_url}/{ad_id}/'
        try:
            return await self._make_request(url, json_response=True)
        except Exception as e:
            logger.error(f"Failed to get offer_data for `{ad_id}`. Error: {e} · {url}")

    async def find_available_offers(self, start: int = None, end: int = None):
        """

        :param start:
        :param end:
        """
        start_n = start or 800_000_000
        end_n = end or 900_000_000

        for i in range(start_n, end_n):
            url = f'{self.__base_url}/api/v1/offers/{i}/'
            response = await self._make_request(url)

            data = json.loads(response)
            if 'error' in data:
                logger.error(f"{url} · {data.get('error', {}).get('status')}")
                continue

            if not data:
                logger.info(f"{url} · {data}")

            if data:
                title = data.get('data', {}).get('title')
                ad_url = data.get('data', {}).get('url')
                logger.info(f"{title} · {url} · {ad_url}")

    async def _get_challenge_context(self, ad_id: OfferID, ad_url: str) -> Context | None:
        """

        """
        username = str(uuid.uuid4())
        url = 'https://friction.olxgroup.com/challenge'

        headers = self._get_headers().update({'x-user-tests': 'eyJkZWx1YXJlYi0zNjgwIjoiYSIsImR2LTMyMzkiOiJiIiwiam9icy04NjE3IjoiYSIsImpvYnMtODYzNiI6ImIiLCJvZWNzLTEwMDIiOiJjIiwib2x4ZXUtNDI0NDgiOiJiIiwicG9zLTEwNzciOiJiIn0='})
        payload = {
            'action': 'reveal_phone_number',
            'aud': 'atlas',
            'actor': {
                'username': username,
            },
            'scene': {
                'origin': 'www.olx.ua',
                'sitecode': 'olxua',
                'ad_id': ad_id,
            },
        }

        response = await self._make_request(url, headers, payload)
        try:
            data = json.loads(response)
            context = data.get('context')
            if not context:
                if data.get('challenge', {}).get('type') == 'blocked':
                    logger.error(f"Failed to get challenge_context for `{ad_id}`. Message: IP Blocked")
                    return None

                current_time = int(time.time())
                wait_until_timestamp = int(data.get('challenge', {}).get('config', {}).get('waitUntil'))

                wait_until_datetime = datetime.utcfromtimestamp(wait_until_timestamp)
                remaining_time = wait_until_timestamp - current_time

                hours = remaining_time // 3600
                remaining_seconds = remaining_time % 3600
                minutes = remaining_seconds // 60
                seconds = remaining_seconds % 60

                formatted_datetime = wait_until_datetime.strftime("%Y-%m-%d %H:%M:%S UTC")
                formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"

                logger.error(f"Failed to get challenge_context for `{ad_id}`. Message: Too many requests. Try in {formatted_datetime}. Remain: {formatted_time} · {ad_url}")
                return None

            logger.debug(f"{username=} · {context=}")
            return Context(value=context)

        except Exception as e:
            logger.error(f"Failed to get challenge_context for `{ad_id}`. Error: {e} · {ad_url}")

    async def _get_authorization_token(self, context: Context, ad_url: str) -> Token | None:
        """

        """
        url = 'https://friction.olxgroup.com/exchange'
        headers = self._get_headers()
        payload = {
            'context': context,
            'response': ''
        }

        response = await self._make_request(url, headers, payload)
        try:
            data = json.loads(response)
            authorization_token = data.get('token')
            if not authorization_token:
                logger.error(f"Failed to get authorization_token. Message: {data.get('error')} · {ad_url}")
                return None

            logger.debug(f"{authorization_token=}")
            return Token(value=authorization_token)

        except Exception as e:
            logger.error(f"Failed to get authorization_token. Error: {e} · {ad_url}")

    async def get_regions(self, sorting_by='id') -> list[Region]:
        """
        Возвращает сортированный по ID список регионов
        :return:
        """
        url = 'https://www.olx.ua/api/v1/geo-encoder/regions/'

        response = await self._make_request(url, json_response=True)
        data = response.get('data', [])

        if sorting_by == 'id':
            regions = sorted([(item.get('id'), item.get('name')) for item in data], key=lambda x: x[0])
        elif sorting_by == 'name':
            regions = sorted([(item.get('id'), item.get('name')) for item in data], key=lambda x: x[1])
        else:
            regions = [(item.get('id'), item.get('name')) for item in data]

        if self._save_json:
            save_json(data, os.path.join(self.out_dir, 'olx__regions.json'))
        return [Region(id=item[0], name=item[1]) for item in regions]

    async def get_cities(self, region: Region, sorting_by='id') -> list[City]:
        """
        Возвращает список ID городов выбранного регона
        :param sorting_by: Сортировка (id, name)
        :param region: ID региона 1-25
        :return:
        """
        url = f'https://www.olx.ua/api/v1/geo-encoder/regions/{region.id}/cities/?limit=5000'

        response = await self._make_request(url, json_response=True)
        data = response.get('data')

        if sorting_by == 'id':
            cities = sorted([(item.get('id'), item.get('name')) for item in data], key=lambda x: x[0])
        elif sorting_by == 'name':
            cities = sorted([(item.get('id'), item.get('name')) for item in data], key=lambda x: x[1])
        else:
            cities = [(item.get('id'), item.get('name')) for item in data]

        if self._save_json:
            save_json(data, os.path.join(self.out_dir, f'{region.id}_{region.name}__cities.json'))
        return [City(id=item[0], name=item[1]) for item in cities]

    async def get_offers_count(self, category_id, region_id=None, city_id=None, facet_field='region') -> OffersMeta:
        """
        Получает общее, видимое и количество объявлений в регионах по ID Категории. И дополнительно по ID Региона и ID Города

        :param city_id:
        :param region_id:
        :param category_id:
        :param facet_field: region / district
        """
        headers = {'accept-language': 'ru'}

        facet_data = json.loads('[{"field":"region","fetchLabel":true,"fetchUrl":true,"limit":199}]')[0]
        facet_data['field'] = facet_field

        params = {
            'offset': '0',
            'limit': '40',
            'category_id': category_id,
            'filter_refiners': 'spell_checker',
            'facets': json.dumps([facet_data]),
        }

        if region_id:
            params['region_id'] = region_id
        if city_id:
            params['city_id'] = city_id

        url = str(URL('https://www.olx.ua/api/v1/offers/metadata/search/').with_query(params))
        response = await self._make_request(url, headers, json_response=True)
        data = response.get('data', [])

        regions = [
            Region(id=item.get('id'), count=item.get('count'), name=item.get('label'), url=f"https://www.olx.ua/{item.get('url').strip('/')}")
            for item
            in data.get('facets', {}).get(facet_field, [])
        ]

        if self._save_json:
            save_json(data, os.path.join(self.out_dir, f'category_{category_id}_{region_id}_{city_id}__offers_count.json'))
        return OffersMeta(data.get('visible_total_count'), data.get('total_count'), regions)

    async def get_category_name(self, category_id):
        params = {
            'params[category_id]': category_id,
            'page': 'ads',
            'params[offset]': '0',
            'params[limit]': '40',
            'params[currency]': 'UAH',
            'params[filter_refiners]': 'spell_checker',
            'params[viewType]': 'gallery',
            'dfp_user_id': '0',
            'advertising_test_token': '',
        }

        url = str(URL('https://www.olx.ua/api/v1/targeting/data/').with_query(params))
        response = await self._make_request(url, json_response=True)
        targeting = response.get('data', []).get('targeting', {})
        return ' > '.join([v for k, v in targeting.items() if 'name' in k])

    async def get_offers_from_page(self, category_url) -> list[dict]:
        """
        Получает список объявлений со всех страниц категории(ссылки).

        1. Определяется количество страниц в категории.
        2. Для каждой страницы извлекает информацию о предложениях.
        3. Парсит данные с помощью BeautifulSoup и регулярных выражений.
        4. Возвращает список словарей с данными по каждому объявлению (идентификатор, URL, заголовок и контакт).

        :param category_url: URL категории, с которой необходимо получить предложения.
                             Должен быть корректным URL для страницы с товарами или объявлениями.
        :return: Список словарей, каждый из которых содержит информацию о предложении.
                 Каждый словарь имеет следующие ключи:
                    - 'id' (str): Уникальный идентификатор объявления.
                    - 'url' (str): URL страницы объявления.
                    - 'title' (str): Заголовок объявления.
                    - 'contact' (dict): Контактная информация (если доступна) из объявления.

        Пример возвращаемого результата:
        [
            {
                'id': '868972409',
                'url': 'https://www.olx.ua/api/v1/offers/868972409',
                'title': 'Продается видеокарта',
                'contact': {
                    "name": "AMAZIN інтернет магазин",
                    "phone": true,
                    "chat": true,
                    "negotiation": true,
                    "courier": true
                }
            },
            ...
        ]
        """

        result = []
        self._category_url = category_url

        total_pages = await self._pagination(category_url)
        tasks = [
            self._make_request(f'{category_url}/?page={page + 1}')
            for page
            in range(total_pages)
        ]

        results = await tqdm_asyncio.gather(*tasks, desc=self._txt_all_offers, ncols=self._cols, bar_format=self._bar, ascii=' ▱▰')
        for response in results:
            html = self._get_html(response)
            data = self._find_json(html)

            products = data.get('listing', {}).get('listing', {}).get('ads', [])
            for n, product in enumerate(products):
                title = product.get('title')
                url = product.get('url')
                result.append(dict(
                    id=product.get('id'),
                    title=title,
                    url=url,
                    contact=product.get('contact'))
                )
                logger.debug(f"[{n}/{len(products)}] |  {title[:50].ljust(50)}  ·  {url}")

        if self._save_json:
            await save_json(result, os.path.join(self.out_dir, 'urls.json'))
        return result

    async def _offers_from_first_page(self, category_id: int, region_id: int = None, city_id: int = None) -> tuple[list, str | None]:
        """
        Получает объявления с первой страницы через API и возвращет ссылку на следующую страницу
        """
        params = {
            'offset': '0',
            'limit': '40',
            'category_id': category_id,
            'currency': 'UAH',
            'filter_refiners': 'spell_checker',
            'facets': '[{"field":"district","fetchLabel":true,"fetchUrl":true,"limit":30}]',
        }
        if region_id:
            params['region_id'] = region_id
        if city_id:
            params['city_id'] = city_id

        url = str(URL(self.__api_offers_url).with_query(params))
        response = await self._make_request(url, json_response=True)
        offers = response.get('data')

        next_page = response.get('links', {}).get('next', {}).get('href')
        return offers, next_page

    async def get_offers_from_api(self, category_id: int, region_id: int = None, city_id: int = None) -> list[Offer]:
        """
        Получает объявления со всех доступных страниц через API
        """
        all_offers_raw = []
        page = 0

        offers, next_page = await self._offers_from_first_page(category_id, region_id, city_id)
        all_offers_raw.extend(offers or [])

        page_urls = []
        while next_page:
            page += 1
            page_urls.append(next_page)
            response = await self._make_request(next_page, json_response=True)
            next_page = response.get('links', {}).get('next', {}).get('href')
            print(f"\r🔄  Страница {page}", end='', flush=True)

        tasks = [
            self._make_request(url, json_response=True)
            for url
            in page_urls
        ]
        results = await tqdm_asyncio.gather(*tasks, desc=self._txt_all_offers, ncols=self._cols, bar_format=self._bar, leave=False, ascii=' ▱▰')

        for response in results:
            all_offers_raw.extend(response.get('data', []))

        return [self._format_offer(offer) for offer in all_offers_raw]

    async def get_offers_from_graphql(self, page=None, category_id=None, region_id=None, city_id=None, currency=None):
        if page is None or page < 1:
            page = 1
        offset = (page - 1) * limit

        params = [{"key": "limit", "value": str(limit)}, {"key": "offset", "value": str(offset)}]

        if category_id:
            params.append({"key": "category_id", "value": category_id})
        if category_id:
            params.append({"key": "region_id", "value": region_id})
        if category_id:
            params.append({"key": "city_id", "value": city_id})
        if currency:
            if currency.lower() == 'usd':
                params.append({"key": "currency", "value": "USD"})
            if currency.lower() == 'uah':
                params.append({"key": "currency", "value": "UAH"})

        payload = {
            "query": """
                query ListingSearchQuery($searchParameters: [SearchParameter!] = {key: "", value: ""}) {
                  clientCompatibleListings(searchParameters: $searchParameters) {
                    ... on ListingSuccess {
                      metadata { total_elements visible_total_count }
                      links { self { href } }
                      data {
                        id
                        title
                        status
                        url
                        description
                        protect_phone
                        contact { courier chat name negotiation phone }
                        category { id type }
                        location { city { id name normalized_name } district { id name } region { id name } }
                        params { key value { ... on PriceParam { value currency converted_value converted_currency label } } }
                      }
                    }
                  }
                }
            """,
            "variables": {
                "searchParameters": params
            }
        }

        url = 'https://www.olx.ua/apigateway/graphql'
        response = await self._make_request(url, payload=payload, json_response=True)
        data = response.get('data', {})

        if self._save_json:
            save_json(data, os.path.join(self.out_dir, f'{category_id}_{region_id}_{city_id}__offers_graphql.json'))
        return data.get('clientCompatibleListings', {}).get('data', {})

    async def get_items_count_for_all_categories(self, region_id=None, city_id=None, region_name=None, city_name=None, sorting_by='id') -> list[Category]:
        """
        Возвращает количество объявлений в каждой категории по ID региона или ID города
        """
        headers = {'accept-language': 'ru'}

        params = {}
        if region_id:
            params['region_id'] = region_id
        if city_id:
            params['city_id'] = city_id

        url = str(URL('https://www.olx.ua/api/v1/offers/metadata/search-categories/').with_query(params))
        response = await self._make_request(url, headers, json_response=True)
        data = response.get('data', {}).get('categories')

        if sorting_by == 'id':
            categories = sorted(data, key=lambda item: item.get('id', 0))
        elif sorting_by == 'count':
            categories = sorted(data, key=lambda item: item.get('count', 0))
        else:
            categories = data

        if self._save_json:
            save_json(data, os.path.join(self.out_dir, f'{region_id}_{region_name}_{city_name}__categories.json'))
        return [Category(id=item['id'], count=item['count'], name=None) for item in categories]

    async def get_phone_numbers(self, ad_id: OfferID, ad_url: str) -> list[str, ...]:
        """

        """
        numbers = []
        url = f'{self.__base_url}/api/v1/offers/{ad_id}/limited-phones/'

        context = await self._get_challenge_context(ad_id, ad_url)
        token = await self._get_authorization_token(context, ad_url)

        headers = {
            'accept': '*/*',
            'accept-language': 'uk',
            'friction-token': token,
            'priority': 'u=1, i',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'x-client': 'DESKTOP',
            'x-device-id': 'aad787b0-7b98-4713-8c81-138e4e6a8cf5',
            'x-platform-type': 'mobile-html5',
        }

        if not context and not token:
            logger.error(f"Failed to get phone_numbers for `{ad_id}` · {ad_url}")
            return numbers

        try:
            response = await self._make_request(url, headers=headers, json_response=True)
            data = response.get('data', {}).get('phones', [])
            if not numbers:
                status = data.get('error').get('status')
                error = data.get('error').get('title')
                message = data.get('error').get('detail')
                logger.error(f"Failed to get phone_numbers for `{ad_id}` · {error} {status} · {message} · {ad_url}")
            return numbers

        except Exception as e:
            logger.error(f"Failed to get phone_numbers for `{ad_id}`. Error: {e} · {ad_url}")

    async def fetch_and_write_phone(self, n, item, ws, wb, wb_path, save_every_n, pbar):
        offer_id = item[0]
        has_phone = item[2]
        url = item[10]
        row_idx = n + 2
        number_cell = ws.cell(row=row_idx, column=3)

        if isinstance(has_phone, str) and has_phone == 'False':
            number_cell.value = 'не указан'
            number_cell.style = 'not_found_style'
            pbar.set_description_str(f"SKIPPED:  Не указан номер")
            pbar.update(1)
            time.sleep(0.5)
            return

        if isinstance(has_phone, str) and has_phone in ('скрыт', 'удален'):
            pbar.set_description_str(f"SKIPPED:  Номер скрыт или объявление удалено")
            pbar.update(1)
            time.sleep(0.5)
            return

        async with self._semaphore:
            response = await self._make_request(f'{self.__api_offers_url}/{offer_id}/limited-phones/', json_response=True, use_proxy=True)

        if 'error' in response:
            error = response.get('error', {}).get('detail')
            if error == 'Disallowed for this user':
                number_cell.value = 'скрыт'
                number_cell.style = 'not_instock_style'
            elif error == 'Ad is not active':
                number_cell.value = 'удален'
                number_cell.style = 'removed_style'
            elif 'Невозможно продолжить' in error:
                number_cell.value = 'Captcha'
            pbar.set_description_str(f"{LIGHT_RED}❌  {error}{WHITE} · {url}")
            time.sleep(0.5)
        else:
            phones_data = response.get('data', {}).get('phones', [])
            number = phones_data[0] if phones_data else None
            if number:
                number_cell.value = number
                number_cell.style = 'active_style'
                pbar.set_description_str(f"{LIGHT_GREEN}✅  {number}{WHITE} · {url}")
                time.sleep(0.5)

        pbar.update(1)

        # Сохраняем прогресс каждые N итераций
        if (n + 1) % save_every_n == 0:
            async with self._save_lock:
                wb.save(wb_path)

    async def parse_phones_from_file(self, filename):
        logger.info('🔄  Начинается сбор номеров из файла')
        if app_config.USE_PROXY:
            logger.info("ℹ️  Использование прокси включено")
        time.sleep(1)

        # Путь до merged таблицы
        wb_path = os.path.join(self.data_dir, filename)

        # Открываем файл и делаем первую страницу активной
        with yaspin(text="Чтение файла") as spinner:
            wb = load_workbook(wb_path)
            ws = wb.active
            spinner.ok('✅  Готово')

        # Добавляем стили ячеек в книгу
        register_styles(wb)

        # Получаем офферы из таблицы начиная со второй строки и до конца в виде списка
        offers_data = list(ws.iter_rows(min_row=2, values_only=True))
        total_offers = len(offers_data)
        save_every_n = 10

        pbar = tqdm_asyncio(total=total_offers, desc='🔄  Парсим номер телефонов', bar_format=self._bar, ncols=self._cols, leave=False, ascii=' ▱▰')

        tasks = [
            self.fetch_and_write_phone(n, item, ws, wb, wb_path, save_every_n, pbar)
            for n, item
            in enumerate(offers_data)
        ]

        await asyncio.gather(*tasks)

        pbar.close()

        with yaspin(text="Сохранение файла") as spinner:
            wb.save(wb_path)
            spinner.ok('✅  Готово')

    async def run(self, region_id=None, city_id=None):
        """
        Запуск парсера. Если передан region_id, то обрабатывается только этот регион.
        """
        logger.info('ℹ️  Начинается сбор объявлений для выбранного региона и города')
        time.sleep(1)

        total_collected = 0
        indexes_path = os.path.join(self.data_dir, 'last_indexes.json')

        # Получаем сохранённые индексы (если есть)
        indexes = open_json(indexes_path) if os.path.exists(indexes_path) else {"region": 0, "city": 0, "category": 0}
        save_json(indexes, indexes_path)

        regions = await self.get_regions()
        if region_id is not None:
            regions = [r for r in regions if r.id == region_id]
            indexes["region"] = 0  # сбрасываем прогресс, чтобы начать с начала выбранного региона

        for n_region, region in enumerate(regions):
            if n_region < indexes["region"]:
                continue  # Пропускаем уже обработанные регионы

            print(f"\n{LIGHT_BLUE}[{n_region + 1} / {len(regions)}]{WHITE} |  🆔  {region.id} · Регион:  {LIGHT_YELLOW}{region.name}{WHITE}")

            cities = await self.get_cities(region)
            if city_id is not None:
                cities = [c for c in cities if c.id == city_id]
                indexes["city"] = 0  # сбрасываем прогресс по городам, чтобы начать с начала выбранного города

            for n_city, city in enumerate(cities):
                if n_region == indexes["region"] and n_city < indexes["city"]:
                    continue  # Пропускаем уже обработанные города

                categories = await self.get_items_count_for_all_categories(region.id, city.id, region.name, city.name)

                if not categories:
                    print(f"{LIGHT_BLUE}[{n_city + 1} / {len(cities)}]{WHITE} |  🆔  {city.id} · Город:  {LIGHT_YELLOW}{city.name}{WHITE} | Объявлений не найдено")
                else:
                    print(f"{LIGHT_BLUE}[{n_city + 1} / {len(cities)}]{WHITE} |  🆔  {city.id} · Город:  {LIGHT_YELLOW}{city.name}{WHITE}")
                    print('─' * 50)

                    for n_category, category in enumerate(categories):
                        if n_region == indexes["region"] and n_city == indexes["city"] and n_category < indexes["category"]:
                            continue  # Пропускаем уже обработанные категории

                        category_name = await self.get_category_name(category.id)
                        offers = await self.get_offers_from_api(category.id, region.id, city.id)
                        save_offers(offers, region_id, region.name, city.id, city.name, category.id, category_name, self.out_dir, self._save_json, self._save_xls)

                        offers_count = await self.get_offers_count(category.id, region.id, city.id)
                        total_pages = (offers_count.visible_total + limit - 1) // limit
                        max_offers = offers_count.visible_total

                        total_collected += max_offers
                        print(f"{LIGHT_BLUE}[{n_category + 1} / {len(categories)}]{WHITE} |   🆔  {category.id} · {YELLOW}{category_name[:100].ljust(100)}{WHITE} | "
                              f"📰  {BOLD}{LIGHT_MAGENTA}{offers_count.total}{RESET} / "
                              f"📚  {BOLD}{LIGHT_CYAN}{total_pages}{RESET}{WHITE} / "
                              f"📥  {BOLD}{RED}{max_offers}{RESET}{WHITE} / "
                              f"📦  {total_collected}")
                        # save_json({"region": n_region, "city": n_city, "category": n_category + 1}, indexes_path)

                    print('─' * 50)
                    time.sleep(1)
                    logger.info(f"✅  Сбор объявлений по всем категориям в {LIGHT_YELLOW}{region.name}{WHITE} города {LIGHT_YELLOW}{city.name}{WHITE} завершен")
                    merge_city_offers(self.data_dir, region.name, region.id, city.name, city.id, self._bar)

                break

            # indexes["city"] = 0
            # indexes["category"] = 0
            # save_json({"region": n_region, "city": 0, "category": 0}, indexes_path)

            break

        logger.info(f"✅  Парсинг завершён. Всего собрано объявлений: {total_collected}")
        os.startfile(self.data_dir)

        print('\n[процесс завершил работу с кодом 0]')
        while True:
            answer = input(f"Теперь вы можете закрыть этот терминал с помощью клавиши {UNDERLINED}Q{RESET}{WHITE}. Или нажмите клавишу {UNDERLINED}ENTER{RESET}{WHITE} для перезапуска.")
            if answer.lower() == 'q' or answer.lower() == 'й':
                break
            os.system("cls")
            os.execl(sys.executable, sys.executable, *sys.argv)
