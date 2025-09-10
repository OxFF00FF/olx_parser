import asyncio
import os
import platform
import sys
import traceback
from time import perf_counter

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.menu import banner, main_menu, choose_region, choose_city, choose_file, choose_parsed_city, authorize
from Src.parser.credentials import get_token
from Src.parser.olx import olxParser
from Src.parser.utils import format_proxies

__version__ = 'v 1.2.0'


async def main():
    start = perf_counter()

    try:
        parser = olxParser(Xlsx=True)

        banner(__version__)
        format_proxies()
        await main_menu()

        choice = input(f'{CYAN}▶️Выберите действие ({WHITE}{BOLD}1/2/3/4{RESET}{CYAN}): {WHITE}')
        if choice == '1':
            # Выбор регоина
            region = await choose_region(parser)

            # Выбор города
            city = await choose_city(parser, region)

            # Отправляем ID Региона и ID Города в парсер
            await parser.run(region.id, city.id)

        elif choice == '2':
            await get_token(exp_time_only=True, show_info=False)
            choosed_filename = choose_file()
            await parser.parse_phones_from_file(choosed_filename, show_info=True)

        elif choice == '3':
            parsed_files = choose_parsed_city()
            for n_file, filepath in enumerate(parsed_files):
                filename = os.path.basename(filepath)

                if os.path.basename(filename).startswith('+'):
                    continue

                await get_token(exp_time_only=True, show_info=False)
                print(f"[{LIGHT_BLUE}{n_file + 1} / {len(parsed_files)}{WHITE}]  {filename}")
                await parser.parse_phones_from_file(filepath, show_info=False)
            print(f"✔️  Все файлы в обработаны")

        elif choice == '4':
            parsed_files = choose_parsed_city()
            parser.merge_parsed_files(parsed_files)

        elif choice == '5':
            authorize()

        elif '-' in choice:
            parts = choice.split('-')
            region_id = int(parts[1])
            city_id = int(parts[2])
            await parser.run(region_id, city_id)

        else:
            print(f"❌  Такой опции нет: {LIGHT_RED}{choice}{WHITE} \n")
            input('\nДля Перезапуска нажмите Enter . . .')
            os.execl(sys.executable, sys.executable, *sys.argv)

    except Exception as e:
        logger.error(f"🚫  Произошла неожиданная ошибка: {e}")
        logger.error(traceback.format_exc())
        print('\n[процесс завершил работу с кодом 1]')
        input('Для выхода нажмите Enter . . .')

    finally:
        end = perf_counter() - start
        print('\n')
        logger.info(f"[Finished in {end:.2f}s]")

        print('\n[процесс завершил работу с кодом 0]')
        while True:
            answer = input(f"Теперь вы можете закрыть этот терминал с помощью клавиши {UNDERLINED}Q{RESET}{WHITE}. Или нажмите клавишу {UNDERLINED}ENTER{RESET}{WHITE} для перезапуска.")
            if answer.lower() == 'q' or answer.lower() == 'й':
                break
            os.system("cls")
            os.execl(sys.executable, sys.executable, *sys.argv)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        input('\nВы звершили работу парсера. Для Перезапуска нажмите Enter . . .')
        os.execl(sys.executable, sys.executable, *sys.argv)
