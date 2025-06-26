import asyncio
import os
import platform
import traceback
from time import perf_counter

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.menu import banner, main_menu, choose_region, choose_city, choose_file, choose_parsed_city, authorize
from Src.parser.credentials import get_token
from Src.parser.olx import olxParser
from Src.parser.utils import format_proxies

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    start = perf_counter()

    try:
        format_proxies()
        banner()
        main_menu()

        parser = olxParser(max_workers=10, Xlsx=True)

        choice = input(f'{CYAN}▶️  Выберите действие ({WHITE}{BOLD}1/2/3{RESET}{CYAN}): {WHITE}')
        if choice == '1':
            # Выбор регоина
            region = await choose_region(parser)

            # Выбор города
            city = await choose_city(parser, region)

            # Отправляем ID Региона и ID Города в парсер
            await parser.run(region.id, city.id)

        elif choice == '2':
            choosed_filename = choose_file()
            await parser.parse_phones_from_file(choosed_filename, show_info=True)

        elif choice == '3':
            parsed_files = choose_parsed_city()
            for n_file, filepath in enumerate(parsed_files):
                filename = os.path.basename(filepath)

                if os.path.basename(filename).startswith('+'):
                    continue

                await get_token(show_info=True)
                print(f"{LIGHT_BLUE}[{n_file + 1} / {len(parsed_files)}]{WHITE}  {filename}")
                await parser.parse_phones_from_file(filepath, show_info=False)

        elif choice == '4':
            await authorize()

        else:
            print(f"❌  Такой опции нет: {LIGHT_RED}{choice}{WHITE} \n")
            exit()

    except Exception as e:
        logger.error(f"🚫  Произошла неожиданная ошибка: {e}")
        logger.error(traceback.format_exc())
        print('\n[процесс завершил работу с кодом 1]')
        input('Для выхода нажмите Enter . . .')

    finally:
        end = perf_counter() - start
        print('\n')
        logger.info(f"[Finished in {end:.2f}s]")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        input('\nВы звершили работу парсера. Для выхода нажмите Enter . . .')
        exit()
