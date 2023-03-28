from flask.cli import FlaskGroup
from project import app, db
from flask_apscheduler import APScheduler
from project.functions import (
    delete_and_update_data_in_db,
    add_new_data_in_db,
    add_data_to_db,
    update_the_price_relative_to_the_dollar,
)
from project.models import TableGoogleSheets

cli = FlaskGroup(app)
scheduler = APScheduler()


@cli.command("drop_db")
def drop_db() -> None:
    """
    Удаляет таблицы БД.
    """
    db.drop_all()
    db.session.commit()


@cli.command("create_db")
def create_db() -> None:
    """
    Создает таблицы БД.
    """
    db.create_all()
    db.session.commit()


@cli.command("first_add_data_to_db")
def first_add_data_to_db() -> None:
    """
    Заполняет базу данных данными, полученными из Google таблицы,
    при запуске приложения.
    """
    add_data_to_db()


def start_scheduler_1() -> None:
    """
    Инициирует работу функции 'delete_and_update_data_in_db' каждые 10 секунд.
    """
    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(
        id="scheduled_task",
        func=delete_and_update_data_in_db,
        trigger="interval",
        seconds=10,
        max_instances=2,
    )


def start_scheduler_2() -> None:
    """
    Инициирует работу функции 'add_new_data_in_db' каждые 10 секунд.
    """
    scheduler.pause()
    scheduler.add_job(
        id="scheduled_task_2",
        func=add_new_data_in_db,
        trigger="interval",
        seconds=30,
        max_instances=2,
    )
    scheduler.resume()

def start_scheduler_3() -> None:
    """
    Инициирует работу функции 'update_the_price_relative_to_the_dollar' каждые 24 часа.
    """
    scheduler.pause()
    scheduler.add_job(
        id="scheduled_task_3",
        func=update_the_price_relative_to_the_dollar,
        trigger="interval",
        hours=24,
        max_instances=2,
    )
    scheduler.resume()

if __name__ == "__main__":
    start_scheduler_1()
    start_scheduler_2()
    start_scheduler_3()
    
    cli()
