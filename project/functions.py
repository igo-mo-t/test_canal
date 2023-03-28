from . import db, app
from project.models import TableGoogleSheets
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests
import xmltodict


def get_data_from_table_google_sheets() -> list[list]:
    """
    Используя файл .json с закрытыми ключами, авторизуется в системе Google Sheets,
    возвращает список списков данных из гугл таблицы.
    """

    CREDENTIALS_FILE = "myproject-for-test-381422-af946f8dc4a6.json"

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE,
        [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    httpAuth = credentials.authorize(httplib2.Http())
    service = apiclient.discovery.build("sheets", "v4", http=httpAuth)

    ranges = ["Лист1!A2:D"]

    results = (
        service.spreadsheets()
        .values()
        .batchGet(
            spreadsheetId="1NMiT_H6LMGfMy6AxNyxRRZxp_kGLrpA4OWsFDIU4er8",
            ranges=ranges,
            valueRenderOption="FORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING",
        )
        .execute()
    )

    data_from_table_google_sheets = results["valueRanges"][0]["values"]

    return data_from_table_google_sheets


def data_format_check_from_google_sheets(*args) -> bool:
    "Проверяет данные из Google Sheets на возможность форматирования"
    try:
        par1 = int(args[0])
        par2 = int(args[1])
        par3 = float(args[2])
        par4 = datetime.strptime(args[3], "%d.%m.%Y").date()

        return True
    except Exception:
        return False


def convert_data_from_google_sheet_to_db_format() -> (
    list[tuple[int, int, float, datetime.date]]
):
    """
    Конвертирует и возвращает полученные из get_data_from_table_google_sheets() данные
    в список кортежей, для каждой полностью заполненной строки в таблице Google.
    """

    converted_data_from_google_sheet = [
        (
            int(object_from_table_google_sheets[0]),
            int(object_from_table_google_sheets[1]),
            float(object_from_table_google_sheets[2]),
            datetime.strptime(object_from_table_google_sheets[3], "%d.%m.%Y").date(),
        )
        for object_from_table_google_sheets in get_data_from_table_google_sheets()
        if len(object_from_table_google_sheets) == 4
        and data_format_check_from_google_sheets(
            object_from_table_google_sheets[0],
            object_from_table_google_sheets[1],
            object_from_table_google_sheets[2],
            object_from_table_google_sheets[3],
        )
    ]
    return converted_data_from_google_sheet


def get_today_date_for_request_arg() -> str:
    """
    Преобразует и возвращает текущую дату в формате,
    необходимом для передачи параметра запроса, получаещего курс доллара по API ЦБ РФ.
    """

    today_date = str(datetime.now().date())
    today_date_for_request_arg = f"{today_date[8]}{today_date[9]}/{today_date[5]}{today_date[6]}/{today_date[0]}{today_date[1]}{today_date[2]}{today_date[3]}"

    return today_date_for_request_arg


def get_dollar_exchange_rate() -> float:
    """
    Получает и возвращает значение курса доллара по API ЦБ РФ.
    Если в XML источнике произошли изменения в порядке данных поднимает исключение.
    """

    response = requests.get(
        f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={get_today_date_for_request_arg()}"
    )
    dict_data = xmltodict.parse(response.content)

    data_checking = dict_data["ValCurs"]["Valute"][13]["Name"]

    if data_checking == "Доллар США":
        dollar_exchange_rate_string = dict_data["ValCurs"]["Valute"][13]["Value"]
        dollar_exchange_rate = float(dollar_exchange_rate_string.replace(",", "."))
        return dollar_exchange_rate

    raise Exception(
        "Необходимо проверить источник XML c ресурса ЦБ РФ, получаемое значение не является курсом доллара США"
    )


def calculate_the_price_in_ruble(price_dollar: float) -> float:
    """
    Рассчитывает и возвращает стоимость заказа в рублях.
    """
    price_ruble = float(f"{price_dollar * get_dollar_exchange_rate():.2f}")
    return price_ruble


def add_data_to_db() -> None:
    """
    Заполняет базу данных данными, полученными из Google таблицы.
    """
    list_of_data_objects = [
        TableGoogleSheets(
            item_number=item_number,
            order_number=order_number,
            price_dollar=price_dollar,
            price_ruble=calculate_the_price_in_ruble(price_dollar),
            delivery_time=delivery_time,
        )
        for item_number, order_number, price_dollar, delivery_time in convert_data_from_google_sheet_to_db_format()
    ]

    db.session.add_all(list_of_data_objects)
    db.session.commit()


def get_data_from_db() -> list[tuple]:
    """
    Получает и возвращает список кортежей всех данных из базы данных.
    """
    data_from_db = (
        db.session.query(
            TableGoogleSheets.item_number,
            TableGoogleSheets.order_number,
            TableGoogleSheets.price_dollar,
            TableGoogleSheets.delivery_time,
        )
        .order_by(TableGoogleSheets.item_number)
        .all()
    )
    return data_from_db


def update_string_in_db(value_from_db: tuple, value_from_google_sheet: tuple) -> None:
    """
    Принимает аргументы для получения нужного объекта базы данных и его обновления.
    Обновляет строку БД.
    """
    object_to_update = (
        db.session.query(TableGoogleSheets)
        .filter(TableGoogleSheets.item_number == value_from_db[0])
        .first()
    )
    object_to_update.item_number = value_from_google_sheet[0]
    object_to_update.price_dollar = value_from_google_sheet[2]
    object_to_update.price_ruble = calculate_the_price_in_ruble(
        value_from_google_sheet[2]
    )
    object_to_update.delivery_time = value_from_google_sheet[3]
    db.session.add(object_to_update)
    db.session.commit()


def delete_string_in_db(value_from_db: tuple) -> None:
    """
    Принимает аргумент для получения нужного объекта базы данных.
    Удаляет строку базы БД.
    """
    object_to_delete = (
        db.session.query(TableGoogleSheets)
        .filter(TableGoogleSheets.item_number == value_from_db[0])
        .first()
    )
    db.session.delete(object_to_delete)
    db.session.commit()


def add_string_in_db(value_from_google_sheet: tuple) -> None:
    """
    Принимает аргумент для создания нового объекта базы данных.
    Добавляет новую строку в БД.

    """
    object_to_add = TableGoogleSheets(
        item_number=value_from_google_sheet[0],
        order_number=value_from_google_sheet[1],
        price_dollar=value_from_google_sheet[2],
        price_ruble=calculate_the_price_in_ruble(value_from_google_sheet[2]),
        delivery_time=value_from_google_sheet[3],
    )
    db.session.add(object_to_add)
    db.session.commit()


def delete_and_update_data_in_db() -> list[tuple]:
    """
    Определяет алгоритм сравнения данных из БД и Google таблицы.
    Удаляет лишние данные из БД или обновляет их при найденных несоответствиях.
    Возвращает измененный список кортежей данных БД.
    """
    with app.app_context():
        data_from_db = get_data_from_db()
        data_from_google_sheet = convert_data_from_google_sheet_to_db_format()

        index_db, index_google_sheet = 0, 0

        while index_db < len(data_from_db):
            try:
                value_from_db = data_from_db[index_db]
                value_from_google_sheet = data_from_google_sheet[index_google_sheet]

                if value_from_db == value_from_google_sheet and index_google_sheet == (
                    len(data_from_google_sheet) - 1
                ):
                    index_db += 1
                    continue

                if value_from_db == value_from_google_sheet:
                    index_db += 1
                    index_google_sheet += 1

                elif value_from_db[1] == value_from_google_sheet[1]:
                    data_from_db[index_db] = value_from_google_sheet
                    update_string_in_db(value_from_db, value_from_google_sheet)
                    index_db += 1
                    index_google_sheet += 1
                else:
                    data_from_db.pop(index_db)
                    delete_string_in_db(value_from_db)

            except Exception:
                continue

        return data_from_db


def add_new_data_in_db() -> None:
    """
    Определяет алгоритм сравнения данных из БД (обновлены и удалены лишние) и Google таблицы.
    Добавляет в БД новые данные при найденных несоответствиях.
    """
    with app.app_context():
        data_from_db = delete_and_update_data_in_db()
        data_from_google_sheet = convert_data_from_google_sheet_to_db_format()

        if data_from_db == []:
            add_data_to_db()

        index_db, index_google_sheet = 0, 0

        while index_google_sheet < len(data_from_google_sheet):
            try:
                value_from_db = data_from_db[index_db]
                value_from_google_sheet = data_from_google_sheet[index_google_sheet]

                if value_from_db == value_from_google_sheet and index_db == (
                    len(data_from_db) - 1
                ):
                    index_google_sheet += 1
                    continue

                if value_from_db == value_from_google_sheet:
                    index_db += 1
                    index_google_sheet += 1
                else:
                    data_from_db.append(value_from_google_sheet)
                    add_string_in_db(value_from_google_sheet)
                    index_google_sheet += 1
            except Exception:
                continue


def get_data_from_db_for_template() -> list[tuple]:
    """
    Получает и возвращает список кортежей данных из БД
    для заполнения таблицы в шаблоне HTML.
    """
    data_from_db_for_template = (
        db.session.query(
            TableGoogleSheets.item_number,
            TableGoogleSheets.order_number,
            TableGoogleSheets.price_dollar,
            TableGoogleSheets.price_ruble,
            TableGoogleSheets.delivery_time,
        )
        .order_by(TableGoogleSheets.item_number)
        .all()
    )
    return data_from_db_for_template


def calculate_total_dollar() -> float:
    """
    Рассчитывает и возвращает сумму всех заказов в долларах.
    """
    list_data_db = db.session.query(TableGoogleSheets.price_dollar).all()
    total_dollar = 0
    for object in list_data_db:
        total_dollar += object[0]

    return float(f"{total_dollar:.2f}")


def calculate_total_rub() -> float:
    """
    Рассчитывает и возвращает сумму всех заказов в рублях.
    """
    list_data_db = db.session.query(TableGoogleSheets.price_ruble).all()
    total_rub = 0
    for object in list_data_db:
        total_rub += object[0]

    return float(f"{total_rub:.2f}")


def update_the_price_relative_to_the_dollar() -> None:
    """
    Обновляет БД колонку price_ruble раз в сутки
    (в сутки т.к. курс доллара ЦБ РФ на дату)
    """
    list_data_db = db.session.query(TableGoogleSheets).all()
    for object_data_db in list_data_db:
        object_data_db.price_ruble = calculate_the_price_in_ruble(
            object_data_db.price_dollar
        )
        db.session.add(object_data_db)

    db.session.commit()
