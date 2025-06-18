import asyncio
import platform
import traceback
from time import perf_counter

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.menu import banner, main_menu, choose_region, choose_city, choose_file
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

        choice = input(f'{CYAN}▶️  Выберите действие ({WHITE}{BOLD}1/2{RESET}{CYAN}): {WHITE}')
        if choice == '1':
            # Выбор регоина
            region = await choose_region(parser)

            # Выбор города
            city = await choose_city(parser, region)

            # Отправляем ID Региона и ID Города в парсер
            await parser.run(region_id=region.id, city_id=city.id)

        elif choice == '2':
            await choose_file(parser)

        else:
            print(f"❌  Такой опции нет: {LIGHT_RED}{choice}{WHITE} \n")
            exit()

    except Exception as e:
        logger.error(f"🚫  Произошла неожиданная ошибка: {e}")
        logger.error(traceback.format_exc())
        print('\n[процесс завершил работу с кодом 1]')
        input('Для выхода нажмите любую клавишу . . .')

    finally:
        end = perf_counter() - start
        logger.info(f"[Finished in {end:.2f}s]")


if __name__ == '__main__':
    asyncio.run(main())
