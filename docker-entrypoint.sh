#!/bin/sh
set -e
python manage.py drop_db
python manage.py create_db
python manage.py first_add_data_to_db
python manage.py run -h 0.0.0.0 -p 5000