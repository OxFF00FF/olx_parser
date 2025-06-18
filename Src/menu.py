import os

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.parser.utils import create_banner


def banner():
    os.system("cls")
    # standard, slant, pepper, cybermedium, ansi_shadow
    create_banner([['olx', LIGHT_CYAN, 'ansi_shadow'],
                   ['parser', WHITE, 'standard']], show=True)


def main_menu():
    print(f'╭───────  ГЛАВНОЕ МЕНЮ  ─────────╮ \n'
          f'1.  {LIGHT_YELLOW}Собрать объявления региона{WHITE} \n'
          f'2.  {LIGHT_YELLOW}Собрать номера из файла{WHITE} \n'
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
    print('\n╭─────────────  ФАЙЛЫ  ──────────────╮ ')
    files = [f for f in os.listdir('Data') if f.endswith('xlsx')]
    for i, filename in enumerate(files, 1):
        print(f'{i}.  {LIGHT_YELLOW}{filename}{WHITE}')
    print('╰─────────────────────────────────────╯ \n')
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
    print(f'ℹ️  Выбран регион: {region.name} ({region.id}) \n')
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

        city = next((c for c in cities if c.id == choosed_city_id), None)
        print(f'ℹ️  Выбран город: {city.name} ({city.id}) \n')
        return city
    else:
        print(f"{RED}❌  Неверный номер города{WHITE} \n")
        exit(1)


async def choose_file(parser):
    os.system("cls")
    files = files_list()
    choosed_file_num = input(f'{CYAN}▶️  Выберите файл (1-{len(files)}): {WHITE}')

    if not choosed_file_num.isdigit():
        print(f"❌  Нет такого файла: {LIGHT_RED}{choosed_file_num}{WHITE}")

    choosed_idx = int(choosed_file_num) - 1
    if 0 <= choosed_idx < len(files):
        os.system("cls")
        choosed_filename = files[choosed_idx]
        await parser.parse_phones_from_file(choosed_filename)
    else:
        print(f"{RED}❌  Неверный номер файла{WHITE}")
