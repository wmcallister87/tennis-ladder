from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    winner = db.Column(db.String(50), nullable=False)
    loser = db.Column(db.String(50), nullable=False)
    winner_games = db.Column(db.Integer, nullable=False)
    loser_games = db.Column(db.Integer, nullable=False)
    set1_w = db.Column(db.Integer)
    set1_l = db.Column(db.Integer)
    set2_w = db.Column(db.Integer)
    set2_l = db.Column(db.Integer)
    set3_w = db.Column(db.Integer, nullable=True)
    set3_l = db.Column(db.Integer, nullable=True)

class SignupResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player = db.Column(db.String(50), nullable=False)
    response = db.Column(db.String(10), nullable=False)  # 'yes' or 'no'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
