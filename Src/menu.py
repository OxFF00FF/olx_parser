import os
import sys
import time

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.parser.authorization import get_session_id
from Src.parser.credentials import get_auth_code, get_access_token, get_token
from Src.parser.utils import create_banner


def banner():
    os.system("cls")
    # standard, slant, pepper, cybermedium, ansi_shadow
    create_banner([['olx', LIGHT_CYAN, 'ansi_shadow'],
                   ['parser', WHITE, 'standard']], show=True)


def main_menu():
    token = get_token(show_info=False)
    session = f'{LIGHT_GREEN}Сессия активна{WHITE}' if token else f'{RED}Необходима авторизация{WHITE}'

    if token:
        print(f'╭───────  ГЛАВНОЕ МЕНЮ  ─────────╮ \n'
              f'1.  {LIGHT_YELLOW}Собрать объявления {LIGHT_BLUE}региона{WHITE} \n'
              f'2.  {LIGHT_YELLOW}Собрать номера из {LIGHT_CYAN}файла{WHITE} \n'
              f'3.  {LIGHT_YELLOW}Собрать номера из {LIGHT_MAGENTA}города{WHITE} \n'
              f'4.  {LIGHT_YELLOW}Объединить файлы {LIGHT_MAGENTA}города{WHITE} \n'
              f'    {session} \n'
              f'╰────────────────────────────────╯ \n')
    else:
        print(f'╭───────  ГЛАВНОЕ МЕНЮ  ─────────╮ \n'
              f'1.  {LIGHT_YELLOW}Собрать объявления {LIGHT_BLUE}региона{WHITE} \n'
              f'2.  {LIGHT_YELLOW}Собрать номера из  {LIGHT_CYAN}файла{WHITE} \n'
              f'3.  {LIGHT_YELLOW}Собрать номера из {LIGHT_MAGENTA}города{WHITE} \n'
              f'4.  {LIGHT_YELLOW}ОБъединить файлы {LIGHT_MAGENTA}города{WHITE} \n'
              f'5.  {LIGHT_YELLOW}Войти в аккаунт{WHITE} \n'
              f'╰────────────────────────────────╯ \n')


def regions_list(regions):
    print('\n╭────────────  РЕГИОНЫ  ──────────────╮ ')
    for n, region in enumerate(regions):
        print(f'{n + 1}.  {LIGHT_YELLOW}{region.name.ljust(25)}{WHITE}  🆔  {region.id}')
    print(f'╰─────────────────────────────────────╯ \n')


def cities_list(cities):
    print('\n╭────────────  ГОРОДА  ────────────╮ ')
    for n, city in enumerate(cities):
        print(f'{n + 1}.  {LIGHT_YELLOW}{city.name.ljust(20)}{WHITE}  🆔  {city.id}')
    print(f'╰─────────────────────────────────────╯ \n')


def files_list():
    print('\n╭─────────────────────  ФАЙЛЫ  ──────────────────────╮ ')
    files = [f for f in os.listdir('Data') if f.endswith('xlsx')]
    for i, filename in enumerate(files, 1):
        print(f'{i}.  {LIGHT_YELLOW}{filename}{WHITE}')
    print('╰────────────────────────────────────────────────────╯ \n')
    return files


async def choose_region(parser):
    os.system("cls")
    regions = await parser.get_regions()
    if not regions:
        logger.error(f'🚫  Не удалось получить список регионов')
        exit(1)

    regions_list(regions)

    choosed_region_id = input(f'{CYAN}▶️  Выберите регион ({WHITE}{BOLD}1-{len(regions)}{RESET}{CYAN}): {WHITE}')
    if not choosed_region_id.isdigit() or int(choosed_region_id) not in [r.id for r in regions]:
        print(f'❌  Нет такого региона: {LIGHT_RED}{choosed_region_id}{WHITE} \n')
        exit(1)

    region = next((r for r in regions if r.id == int(choosed_region_id)), None)
    return region


async def choose_city(parser, region):
    os.system("cls")
    cities = await parser.get_cities(region, sorting_by='name')
    if not cities:
        logger.error(f'🚫  Не удалось получить список городов')
        exit(1)

    cities_list(cities)

    choosed_city_num = input(f'{CYAN}▶️  Выберите город ({WHITE}{BOLD}1-{len(cities)}{RESET}{CYAN}): {WHITE}')

    if not choosed_city_num.isdigit():
        print(f"❌  Нет такого города: {LIGHT_RED}{choosed_city_num}{WHITE} \n")
        exit(1)

    choosed_idx = int(choosed_city_num) - 1
    if 0 <= choosed_idx < len(cities):
        choosed_city_id = cities[choosed_idx].id

        os.system("cls")
        city = next((c for c in cities if c.id == choosed_city_id), None)
        return city
    else:
        print(f"{RED}❌  Неверный номер города{WHITE} \n")
        exit(1)


def choose_file():
    os.system("cls")
    files = files_list()
    choosed_file_num = input(f'{CYAN}▶️  Выберите файл ({BOLD}{WHITE}1-{len(files)}{RESET}{CYAN}): {WHITE}')

    if not choosed_file_num.isdigit():
        print(f"❌  Нет такого файла: {LIGHT_RED}{choosed_file_num}{WHITE}")

    choosed_idx = int(choosed_file_num) - 1
    if 0 <= choosed_idx < len(files):
        os.system("cls")
        return files[choosed_idx]
    else:
        print(f"{RED}❌  Неверный номер файла{WHITE}")


def choose_parsed_city():
    data_dir = 'data'

    os.system("cls")
    parsed_regions = [name for name in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, name)) and '_' in name]
    print('\n╭───────  ПОЛУЧЕННЫЕ РЕГИОНЫ  ───────╮ ')
    for n, region in enumerate(parsed_regions):
        region_name, region_id = region.split('_')
        print(f'{n + 1}.  {LIGHT_YELLOW}{region_name.ljust(25)}{WHITE}  🆔  {region_id}')
    print('╰────────────────────────────────────╯ \n')

    choosed_region_id = input(f'{CYAN}▶️  Выберите регион ({WHITE}{BOLD}1-{len(parsed_regions)}{RESET}{CYAN}): {WHITE}')
    region_dir = next((r for r in parsed_regions if r.split('_')[-1] == choosed_region_id), None)

    os.system("cls")
    parsed_cities = [name for name in os.listdir(os.path.join(data_dir, region_dir)) if os.path.isdir(os.path.join(data_dir, region_dir, name))]
    print('\n╭──────────  ПОЛУЧЕННЫЕ ГОРОДА  ────────╮ ')
    for n, city in enumerate(parsed_cities):
        city_name, city_id = city.split('_')
        files_count = f"({str(len(os.listdir(os.path.join(data_dir, region_dir, city))))})"
        print(f'{n + 1}.  {LIGHT_YELLOW}{city_name.ljust(20)}{WHITE} 🆔  {city_id} {files_count}')
    print(f'╰───────────────────────────────────────╯ \n')

    choosed_city_num = input(f'{CYAN}▶️  Выберите город ({WHITE}{BOLD}1-{len(parsed_cities)}{RESET}{CYAN}): {WHITE}')
    choosed_idx = int(choosed_city_num) - 1
    if 0 <= choosed_idx < len(parsed_cities):
        choosed_city_id = parsed_cities[choosed_idx].split('_')[-1]

        city_dir = next((c for c in parsed_cities if c.split('_')[-1] == choosed_city_id), None)

        os.system("cls")
        print(f"\r✔️  Выбранный регион: {LIGHT_YELLOW}{region_dir}{WHITE}")
        print(f"\r✔️  Выбранынй город:  {LIGHT_YELLOW}{city_dir}{WHITE}")
        time.sleep(2)

        return [
            os.path.join(os.path.join(region_dir, city_dir), file)
            for file
            in os.listdir(os.path.join(data_dir, region_dir, city_dir))
            if file.endswith('xlsx')
        ]


def authorize():
    sid = get_session_id()
    if sid:
        auth_code = get_auth_code(login_sid=sid)
        get_access_token(auth_code)
        print("✔️  Вы успешно вошли в аккаунт")

    else:
        print(f"❌  Не удалось войти. Удалите файлы `authorize.json`, `credentials.json` в папке `data`, папку `chrome/profiles/guest` и повторите еще раз")

    input(f"Нажмите {UNDERLINED}ENTER{RESET}{WHITE} для перезапуска")
    os.execl(sys.executable, sys.executable, *sys.argv)
    exit()
