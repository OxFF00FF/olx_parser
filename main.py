import asyncio
import os
import platform
import traceback
from time import perf_counter

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.menu import banner, main_menu, regions_list, files_list
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
            os.system("cls")
            regions = await parser.get_regions()
            regions_list(regions)

            choosed_region_id = input(f'{CYAN}▶️  Выберите регион ({WHITE}{BOLD}1-{len(regions)}{RESET}{CYAN}): {WHITE}')

            if not choosed_region_id.isdigit() or int(choosed_region_id) not in [r.id for r in regions]:
                logger.error(f'Нет такого региона: {choosed_region_id}')
                exit()

            region = next((r for r in regions if r.id == int(choosed_region_id)), None)
            logger.info(f'ℹ️  Выбран регион: {region.name}(🆔  {region.id})')

            await parser.run(region_id=region.id)

        elif choice == '2':
            os.system("cls")

            files = files_list()
            choosed_num = input(f'{CYAN}▶️  Выберите файл (1-{len(files)}): {WHITE}')
            if choosed_num.isdigit():
                choosed_idx = int(choosed_num) - 1
                if 0 <= choosed_idx < len(files):
                    choosed_filename = files[choosed_idx]
                    await parser.parse_phones_from_file(choosed_filename)
                else:
                    print(f"{RED}❌  Неверный номер файла{WHITE}")
            else:
                print(f"{RED}❌  Введите корректный номер{WHITE}")

        else:
            print(f"\n{LIGHT_RED}🚫  Такой опции нет: {choice}{WHITE}")

    except Exception as e:
        logger.error(f"{RED}🚫  Произошла неожиданная ошибка: {e}{WHITE}")
        logger.error(traceback.format_exc())
        print('\n[процесс завершил работу с кодом 1]')
        input('Для выхода нажмите любую клавишу . . .')

    finally:
        end = perf_counter() - start
        logger.info(f"[Finished in {end:.2f}s]")
        os.startfile('data')


if __name__ == '__main__':
    asyncio.run(main())
