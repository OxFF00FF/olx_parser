import os
import time

from tqdm import tqdm
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, NamedStyle, PatternFill
from openpyxl.utils import get_column_letter

from Src.app.colors import *
from Src.app.logging_config import logger
from Src.parser.schemas import Offer

green_fill = PatternFill(start_color="47ff94", end_color="47ff94", fill_type="solid")
orange_fill = PatternFill(start_color="ff6347", end_color="ff6347", fill_type="solid")
lavender_fill = PatternFill(start_color="baa4fc", end_color="baa4fc", fill_type="solid")
gray_fill = PatternFill(start_color="bbbbbb", end_color="bbbbbb", fill_type="solid")

hlink_style = Font(color="0000FF", underline="single")

number_style = NamedStyle(name="number_style", number_format="0", alignment=Alignment(horizontal='left'))
active_status_style = NamedStyle(name="active_style", fill=green_fill, alignment=Alignment(horizontal='center'))
removed_status_style = NamedStyle(name="removed_style", fill=orange_fill, alignment=Alignment(horizontal='center'))
not_instock_status_style = NamedStyle(name="not_instock_style", fill=lavender_fill, alignment=Alignment(horizontal='center'))
not_found_style = NamedStyle(name="not_found_style", fill=gray_fill, alignment=Alignment(horizontal='center'))


def save_offers_excel(content: list[Offer], filepath: str, show_info=True):
    column_mapping = {
        'id': 'ID',
        'title': 'Объявление',
        'number': 'Номер телефона',
        'selelr_name': 'Продавец',
        'seller_city': 'Город',
        'description': 'Описание',
        'price_usd': 'Стоимость USD',
        'price_uah': 'Стоимость UAH',
        'price_text': 'Цена формат.',
        'posted_date': 'Дата публикации',
        'url': 'Ссылка',
    }

    # Добавление заголовков
    headers = [column_mapping[key] for key in column_mapping.keys()]

    if os.path.exists(filepath):
        wb = load_workbook(filepath)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Товары"
        ws.append(headers)
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

    # Словарь для расчета ширины колонок
    column_widths = {i: len(headers[i - 1]) + 2 for i in range(1, len(headers) + 1)}

    for offer in content:
        row = [
            offer.id,
            offer.title,
            offer.phone_number,
            offer.seller_name or '',
            offer.seller_city or ' ',
            offer.description or ' ',
            offer.price_usd or ' ',
            offer.price_uah or ' ',
            offer.price_str or ' ',
            offer.posted_date or '',
            offer.url or '',
        ]
        ws.append(row)

        # Обновляем максимальную ширину
        for col_num, value in enumerate(row, 1):
            val_str = str(value)
            column_widths[col_num] = max(column_widths[col_num], len(val_str) + 10)
            cell = ws.cell(row=ws.max_row, column=col_num)
            cell.alignment = Alignment(horizontal='left')

        # создание ссылки из названия товара
        product_title_cell = ws.cell(row=ws.max_row, column=2)
        product_title_cell.hyperlink = offer.url
        product_title_cell.font = hlink_style

        # создание ссылки для url
        product_title_cell = ws.cell(row=ws.max_row, column=11)
        product_title_cell.hyperlink = offer.url
        product_title_cell.font = hlink_style

    # Установка ширины колонок
    for col_num, width in column_widths.items():
        ws.column_dimensions[get_column_letter(col_num)].width = min(width, 100)

    try:
        wb.save(filepath)
        if show_info:
            logger.info(f"💾  {LIGHT_GREEN}Excel файл сохранен по пути `{filepath}` {WHITE}")
    except PermissionError as e:
        logger.error(f"Не удалось сохранить EXCEL файл: {e}")


def merge_city_offers(data_dir, region_name, region_id: int, city_name, city_id: int, bar, show_info=None):
    xlsx_path = os.path.join(data_dir, f"{region_name.replace(' ', '-')}_{region_id}", f"{city_name}_{city_id}")
    save_path = os.path.join(data_dir, f"merged_{region_name}_{city_name}.xlsx")

    merged_wb = Workbook()
    output_ws = merged_wb.active
    output_ws.title = f"{region_name} · {city_name}"
    header_written = False
    column_widths = {}

    xlsx_files = [f for f in os.listdir(xlsx_path) if f.endswith('xlsx')]

    progress_bar = tqdm(xlsx_files, bar_format=bar, ncols=150, leave=False, ascii=' ▱▰')

    for filename in progress_bar:
        file_path = os.path.join(xlsx_path, filename)
        progress_bar.set_description_str(f"🔄  Объединение {filename[:40]}...")

        wb = load_workbook(file_path)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        if not rows:
            continue

        # Запись заголовка с форматированием
        if not header_written:
            output_ws.append(rows[0])
            for col_num, header in enumerate(rows[0], 1):
                cell = output_ws.cell(row=1, column=col_num)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')
                column_widths[col_num] = len(str(header)) + 2
            header_written = True
            data_rows = rows[1:]
        else:
            data_rows = rows[1:]

        for row in data_rows:
            output_ws.append(row)

    merged_wb.save(save_path)

    total_rows = output_ws.max_row - 1
    for row in tqdm(output_ws.iter_rows(min_row=2, max_row=output_ws.max_row), total=total_rows, desc="🔄  Форматирование строк", ncols=150, bar_format=bar, leave=False, ascii=' ▱▰'):
        for col_idx, cell in enumerate(row, 1):
            val_str = str(cell.value) if cell.value is not None else ''
            cell.alignment = Alignment(horizontal='left')
            column_widths[col_idx] = max(column_widths.get(col_idx, 0), len(val_str) + 10)

        # Добавление ссылок
        if len(row) >= 11:
            title_cell = row[1]  # 2-я колонка - Название
            url_cell = row[10]  # 11-я колонка - URL
            url = url_cell.value
            if url:
                title_cell.hyperlink = url
                title_cell.font = hlink_style
                url_cell.hyperlink = url
                url_cell.font = hlink_style

    # Установка ширины колонок
    for col_idx, width in column_widths.items():
        output_ws.column_dimensions[get_column_letter(col_idx)].width = min(width, 100)

    try:
        logger.info("💾  Сохранение")
        merged_wb.save(save_path)
        if show_info:
            logger.info(f"💾  {LIGHT_GREEN}Объединенный Excel файл сохранен по пути `{save_path}` {WHITE}")
        time.sleep(1)
        print()

    except PermissionError as e:
        logger.error(f"Не удалось сохранить EXCEL файл: {e}")


def register_styles(wb):
    def add_style(style):
        if style.name not in wb.named_styles:
            wb.add_named_style(style)

    add_style(number_style)
    add_style(active_status_style)
    add_style(removed_status_style)
    add_style(not_instock_status_style)
    add_style(not_found_style)
