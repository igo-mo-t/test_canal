from . import db, app
from project.models import TableGoogleSheets
from typing import Any
import httplib2 
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests
import xmltodict	

def get_data_from_table_google_sheets():
    
    CREDENTIALS_FILE = 'myproject-for-test-381422-af946f8dc4a6.json'  # Имя файла с закрытым ключом, вы должны подставить свое

    # Читаем ключи из файла
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])

    httpAuth = credentials.authorize(httplib2.Http()) # Авторизуемся в системе
    service = apiclient.discovery.build('sheets', 'v4', http = httpAuth) # Выбираем работу с таблицами и 4 версию API
    
    ranges = ["Лист1!A2:D"] # 
          
    results = service.spreadsheets().values().batchGet(spreadsheetId = '1NMiT_H6LMGfMy6AxNyxRRZxp_kGLrpA4OWsFDIU4er8', 
                                     ranges = ranges, 
                                     valueRenderOption = 'FORMATTED_VALUE',  
                                     dateTimeRenderOption = 'FORMATTED_STRING').execute() 
    
    data_from_table_google_sheets = results['valueRanges'][0]['values']
    
    return data_from_table_google_sheets


def convert_data_from_google_sheet_to_db_format():
    # "ИСКЛЮЧЕНИЕ ЕСЛИ НАПРИМЕР СЛОВО В ИНТ "
    
    return [(int(item_number), int(order_number), float(price_dollar), datetime.strptime(delivery_time, '%d.%m.%Y').date()) 
            for item_number, order_number, price_dollar, delivery_time in get_data_from_table_google_sheets()]


def get_today_date_for_request_arg():
    
    today_date = str(datetime.now().date())
    today_date_for_request_arg = f'{today_date[8]}{today_date[9]}/{today_date[5]}{today_date[6]}/{today_date[0]}{today_date[1]}{today_date[2]}{today_date[3]}'
    
    return today_date_for_request_arg



def get_dollar_exchange_rate():
    
    response = requests.get(f'https://www.cbr.ru/scripts/XML_daily.asp?date_req={get_today_date_for_request_arg()}')
    dict_data = xmltodict.parse(response.content)

    
    data_checking = dict_data['ValCurs']['Valute'][13]['Name']
    
    if data_checking == 'Доллар США':
        dollar_exchange_rate_string = dict_data['ValCurs']['Valute'][13]['Value']
        dollar_exchange_rate = float(dollar_exchange_rate_string.replace(',', '.'))
        return dollar_exchange_rate
    
    raise Exception ('Необходимо проверить источник XML, получаемое значение не является курсом доллара США')


def calculate_the_price_in_ruble(price_dollar):
    price_ruble = float(f"{price_dollar * get_dollar_exchange_rate():.2f}")
    return price_ruble


def add_data_to_db():
    list_of_data_objects = [TableGoogleSheets(item_number = item_number,
                                              order_number = order_number, 
                                              price_dollar = price_dollar, 
                                              price_ruble = calculate_the_price_in_ruble(price_dollar), 
                                              delivery_time = delivery_time) 
                            for item_number, order_number, price_dollar, delivery_time in convert_data_from_google_sheet_to_db_format()]
    
    db.session.add_all(list_of_data_objects)
    db.session.commit()
    

def get_data_from_db():
    data_from_db = db.session.query(TableGoogleSheets.item_number, 
                                    TableGoogleSheets.order_number, 
                                    TableGoogleSheets.price_dollar, 
                                    TableGoogleSheets.delivery_time).order_by(TableGoogleSheets.item_number).all()   
    return data_from_db 
    
    
def update_string_in_db(value_from_db, value_from_google_sheet):
    object_to_update = db.session.query(TableGoogleSheets).filter(TableGoogleSheets.item_number == value_from_db[0]).first()
    object_to_update.item_number = value_from_google_sheet[0]
    object_to_update.price_dollar = value_from_google_sheet[2]
    object_to_update.price_ruble = calculate_the_price_in_ruble(value_from_google_sheet[2]) 
    object_to_update.delivery_time = value_from_google_sheet[3]
    db.session.add(object_to_update)
    db.session.commit()
    
    
    
def delete_string_in_db(value_from_db):    
    object_to_delete = db.session.query(TableGoogleSheets).filter(TableGoogleSheets.item_number == value_from_db[0]).first()
    db.session.delete(object_to_delete)
    db.session.commit()
    
    
def add_string_in_db(value_from_google_sheet):
    
    object_to_add = TableGoogleSheets(item_number = value_from_google_sheet[0],
                                      order_number = value_from_google_sheet[1], 
                                              price_dollar = value_from_google_sheet[2], 
                                              price_ruble = calculate_the_price_in_ruble(value_from_google_sheet[2]), 
                                              delivery_time = value_from_google_sheet[3])
    db.session.add(object_to_add)
    db.session.commit()
        
    
def delete_and_update_data_in_db():
    with app.app_context():
        data_from_db = get_data_from_db()
        data_from_google_sheet = convert_data_from_google_sheet_to_db_format()
            
        index_db, index_google_sheet = 0, 0

        while index_db < len(data_from_db):
            value_from_db = data_from_db[index_db]
            value_from_google_sheet = data_from_google_sheet[index_google_sheet]
            
            if value_from_db == value_from_google_sheet and index_google_sheet == (len(data_from_google_sheet) - 1):
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
        
        # db.session.commit()
        
        return data_from_db       
    

def add_new_data_in_db():
    
    with app.app_context():
    
        data_from_db = delete_and_update_data_in_db()
        data_from_google_sheet = convert_data_from_google_sheet_to_db_format()
        
        index_db, index_google_sheet = 0, 0
        
        while index_google_sheet < len(data_from_google_sheet):
            value_from_db = data_from_db[index_db]
            value_from_google_sheet = data_from_google_sheet[index_google_sheet]
            
            if value_from_db == value_from_google_sheet and index_db == (len(data_from_db) - 1):
                index_google_sheet += 1
                continue
            
            if value_from_db == value_from_google_sheet:
                index_db += 1
                index_google_sheet += 1
            else:    
                data_from_db.append(value_from_google_sheet)
                add_string_in_db(value_from_google_sheet)
                index_google_sheet += 1
        
        # db.session.commit()    
    
    
    # from project.functions import add_data_to_db
    
    # from project.functions import delete_and_update_data_in_db()
    # from project.functions import add_new_data_in_db()
    
   