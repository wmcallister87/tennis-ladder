from main import app
from models import SignupResponse
from datetime import datetime, timedelta

with app.app_context():
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    responses = SignupResponse.query.filter(SignupResponse.timestamp >= monday).all()

    for r in responses:
        print(f"{r.player}: {r.response} at {r.timestamp}")
