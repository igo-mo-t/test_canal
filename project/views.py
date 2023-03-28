from project import app
from project.functions import get_data_from_db_for_template, calculate_total_dollar, calculate_total_rub
from flask import render_template


@app.route('/order_data')
def order_data() -> str:
    """
    Возвращает HTML шаблон с данными по заказам.
    """
    return render_template('1.html', 
                           table_data = get_data_from_db_for_template(), 
                           total_dollar = calculate_total_dollar(), 
                           total_rub = calculate_total_rub())

    
