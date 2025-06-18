import os

from Src.app.colors import *
from Src.parser.utils import create_banner


def banner():
    # standard, slant, pepper, cybermedium, ansi_shadow
    create_banner([['olx', LIGHT_CYAN, 'ansi_shadow'],
                   ['parser', WHITE, 'standard']], show=True)


def main_menu():
    print(f'╭──────  ГЛАВНОЕ МЕНЮ  ────────╮ \n'
          f'1.  {LIGHT_YELLOW}Собрать объявления региона{WHITE} \n'
          f'2.  {LIGHT_YELLOW}Собрать номера из файла{WHITE} \n'
          f'╰──────────────────────────────╯ \n')


def regions_list(regions):
    print('\n╭──────  РЕГИОНЫ  ────────╮ ')
    for n, region in enumerate(regions):
        print(f'{n + 1}.  {LIGHT_YELLOW}{region.name}{WHITE}')
    print(f'╰──────────────────────────────╯ \n')


def files_list():
    print('\n╭─────────────  ФАЙЛЫ  ──────────────╮ ')
    files = [f for f in os.listdir('Data') if f.endswith('xlsx')]
    for i, filename in enumerate(files, 1):
        print(f'{i}.  {LIGHT_YELLOW}{filename}{WHITE}')
    print('╰─────────────────────────────────────╯ \n')
    return files
