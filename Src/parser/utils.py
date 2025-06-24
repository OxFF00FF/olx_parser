import itertools
import json
import os
import random
from typing import Callable

from curl_cffi import AsyncSession
from datetime import datetime
from pyfiglet import figlet_format, parse_color

from Src.app.colors import *
from Src.app.config import app_config
from Src.app.logging_config import logger

proxies_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.join(__file__)))), 'proxies.txt')


def open_file(filepath: str) -> str:
    with open(filepath, encoding='utf-8') as file:
        return file.read()


def save_file(filepath: str, content: str):
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)


def save_html(html_text):
    with open(f'index.html', 'w', encoding='utf-8') as file:
        file.write('<meta charset="utf-8">' + html_text)


def save_json(content: list | dict | str, filepath: str = 'data.json'):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(json.dumps(content, ensure_ascii=False, indent=4))

    if app_config.DEBUG:
        logger.debug(f"{GREEN}💾  Data saved to `{os.path.join(filepath)}`{WHITE}")


def open_json(filepath: str = 'data.json'):
    if not os.path.exists(filepath):
        save_json({})

    with open(filepath, encoding='utf-8') as file:
        content = file.read()
        if not content:
            return {}
        else:
            return json.loads(content)


def read_proxies():
    with open(proxies_file, 'r', encoding='utf-8') as file:
        return [item.strip() for item in file.readlines()]


def format_proxies():
    """
    Форматируем прокси в нужный формат
     - <host>:<port>:<login>:<password> -> http://<login>:<password>:<host>:<port>
    """
    result = ''
    files = os.listdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.join(__file__)))))

    not_format_proxies_file = next((f for f in files if f.startswith('Ukraine-resident-proxy')), None)
    if not not_format_proxies_file:
        raise ValueError('Не найден файл с прокси')

    if not_format_proxies_file.endswith('bak'):
        return

    with open(not_format_proxies_file, 'r', encoding='utf-8') as file:
        proxies_list = [item.strip().split(':') for item in file.readlines()]
        for item in proxies_list:
            HOST = item[0]
            PORT = item[1]
            NAME = item[2]
            PASS = item[3]
            result += f"http://{NAME}:{PASS}@{HOST}:{PORT}\n"

    with open(proxies_file, 'w', encoding='utf-8') as file:
        file.write(result)

    os.rename(not_format_proxies_file, f"{not_format_proxies_file}.bak")


def get_proxy() -> Callable[[], str]:
    """
    Выбирает прокси по порядку через каждые {repeat_times} вызовов

    :return: Возвращает функцию которую надо вызвать чтобы получить прокси
    """
    index = 0
    call_count = 0
    proxies = read_proxies()

    def inner() -> str:
        nonlocal index, call_count
        call_count += 1
        if call_count == 2:
            call_count = 0
            index = (index + 1) % len(proxies)
        return proxies[index]

    return inner


def get_proxy_random() -> str:
    proxies = read_proxies()
    return random.choice(proxies)


def get_proxy_next() -> str:
    proxies = read_proxies()
    cycled_proxies = itertools.cycle(proxies)
    return next(cycled_proxies)


async def check_ip(proxy_url):
    async with AsyncSession() as session:
        response = await session.get('https://api.my-ip.io/v2/ip.json', proxy=proxy_url, timeout=20)
        data = response.json()
        logger.info(f"[PROXY {proxy_url.split('@')[-1]} -> {data.get('ip')} / {data.get('country', {}).get('name')} / {data.get('region')} / {data.get('city')}]")


def format_date(iso_date):
    dt = datetime.fromisoformat(iso_date)
    return dt.strftime("%d.%m.%Y в %H:%M:%S")


def current_date():
    """Возвращает текущую дату"""
    return datetime.now().strftime("%Y.%m.%d")


def validate_filename(filename):
    """Убирает запрещенные символы для названия файла"""
    return re.sub(r'[<>:"/\\|?*]', '-', filename)


def get_figlet_text(text, font=None, colors=":", **kwargs):
    ansi_colors = parse_color(colors)
    figlet_text = figlet_format(text, font, **kwargs)

    if ansi_colors:
        figlet_text = ansi_colors + figlet_text + RESET

    return figlet_text


def create_banner(words_and_colors, show=False):
    # Список, который будет содержать строки для каждого текста, с добавленными цветами.
    lines = []
    result = ""

    for (text, color, font) in words_and_colors:
        # Создание ASCII арта для каждого слова из переданного списка
        ascii_art_word = get_figlet_text(text, font, width=200)

        # Разделение арта на список линий
        word_lines = ascii_art_word.splitlines()

        # Красим каждую линию и добавляем в список
        lines.append([
            color + word_line
            for word_line
            in word_lines
        ])

    # Объединяем каждую строку из каждой группы (из разных артов) в одну строку
    for line_group in zip(*lines):
        result += "  ".join(line_group) + "\n"

    if show:
        print(f"\n{result}{WHITE}")

    return result


def clickable_file_link(filepath):
    """Создает кликабельную ссылку в терминале для переданного пута до файла или папки"""
    uri_path = filepath.replace("\\", "/")
    uri = f"file:///{uri_path}"

    # OSC 8 escape-последовательность для ссылки
    esc = "\033]8;;" + uri + "\033\\"
    esc_end = "\033]8;;\033\\"

    return f"{esc}{filepath}{esc_end} {WHITE}({UNDERLINED}CTRL+ПКМ{RESET}{WHITE} чтобы открыть)"
