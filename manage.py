from flask.cli import FlaskGroup
from project import app, db
from flask_apscheduler import APScheduler
from project.functions import delete_and_update_data_in_db, add_new_data_in_db

cli = FlaskGroup(app)
scheduler = APScheduler()

@cli.command("create_db")
def create_db():
    """
    Создает таблицы/БД
    """
    db.create_all()
    db.session.commit()
    
    
def start_scheduler_1():
    """
    Инициирует работу функции 'add_in_database' каждые 10 секунд.
    """
    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(id='scheduled_task', 
                    func=delete_and_update_data_in_db, 
                    trigger='interval', 
                    seconds=10)
        
def start_scheduler_2():
    """
    Инициирует работу функции 'add_in_database' каждые 10 секунд.
    """
    
    scheduler.add_job(id='scheduled_task_2', 
                    func=add_new_data_in_db, 
                    trigger='interval', 
                    seconds=10)

if __name__ == "__main__":
    start_scheduler_1()   
    start_scheduler_2() 
    cli()
    