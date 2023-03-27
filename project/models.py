from project import db


class TableGoogleSheets(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    item_number = db.Column(db.Integer())
    order_number = db.Column(db.Integer())
    price_dollar = db.Column(db.Float())
    price_ruble = db.Column(db.Float())
    delivery_time = db.Column(db.Date())

