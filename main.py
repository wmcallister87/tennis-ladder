from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import math
import os
import re
from models import db, Player, Match, SignupResponse
from matchmaking import generate_weekly_matchups
from elo import calculate_elo

print(">>> Running correct main.py")

app = Flask(__name__)
app.secret_key = "your-secret-key"  # Replace this for production

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def format_phone(phone):
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone

players = {}


@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect("/login")

    leaderboard = calculate_elo()
    all_players = Player.query.order_by(Player.name).all()
    recent_matches = Match.query.order_by(Match.date.desc()).limit(10).all()

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard,
        names=[p.name for p in all_players],
        recent_matches=recent_matches
    )

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@app.route("/submit", methods=["POST"])
def submit():
    if not session.get("logged_in"):
        return redirect("/login")

    p1 = request.form["player1"]
    p2 = request.form["player2"]
    set1_p1 = safe_int(request.form.get("set1_p1"))
    set2_p1 = safe_int(request.form.get("set2_p1"))
    set3_p1 = safe_int(request.form.get("set3_p1"))
    set1_p2 = safe_int(request.form.get("set1_p2"))
    set2_p2 = safe_int(request.form.get("set2_p2"))
    set3_p2 = safe_int(request.form.get("set3_p2"))
    date_str = request.form["date"]
    date = datetime.strptime(date_str, "%Y-%m-%d")

    sets_won_p1 = sum([
        set1_p1 > set1_p2,
        set2_p1 > set2_p2,
        set3_p1 > set3_p2 if (set1_p1 or set1_p2 or set2_p1 or set2_p2) else False
    ])
    sets_won_p2 = 3 - sets_won_p1

    winner = p1 if sets_won_p1 > sets_won_p2 else p2
    loser = p2 if winner == p1 else p1

    winner_games = set1_p1 + set2_p1 + set3_p1 if winner == p1 else set1_p2 + set2_p2 + set3_p2
    loser_games = set1_p1 + set2_p1 + set3_p1 if loser == p1 else set1_p2 + set2_p2 + set3_p2

    match = Match(
        winner=winner,
        loser=loser,
        winner_games=winner_games,
        loser_games=loser_games,
        set1_w=set1_p1 if winner == p1 else set1_p2,
        set1_l=set1_p2 if winner == p1 else set1_p1,
        set2_w=set2_p1 if winner == p1 else set2_p2,
        set2_l=set2_p2 if winner == p1 else set2_p1,
        set3_w=set3_p1 if winner == p1 else set3_p2,
        set3_l=set3_p2 if winner == p1 else set3_p1,
        date=date
    )

    db.session.add(match)
    db.session.commit()

    return redirect("/")

@app.route("/manage-players", methods=["GET", "POST"])
def manage_players():
    if not session.get("logged_in"):
        return redirect("/login")

    if request.method == "POST":
        print("POST received:", request.form)
        action = request.form.get("action")

        if action == "add":
            name = request.form["name"]
            email = request.form["email"]
            phone = format_phone(request.form["phone"])
            new_player = Player(name=name, email=email, phone=phone)
            db.session.add(new_player)
            db.session.commit()

        elif action in ["update", "delete"]:
            player_id = request.form.get("player_id")
            player = Player.query.get(player_id)
            if player:
                if action == "update":
                    player.name = request.form["name"]
                    player.email = request.form["email"]
                    player.phone = format_phone(request.form["phone"])
                elif action == "delete":
                    db.session.delete(player)
                db.session.commit()

        return redirect("/manage-players")

    all_players = Player.query.order_by(Player.name).all()
    return render_template("manage_players.html", players=all_players)

@app.route("/edit-matches", methods=["GET"])
def edit_matches():
    if not session.get("logged_in"):
        return redirect("/login")

    all_matches = Match.query.order_by(Match.date.desc()).all()
    return render_template("edit_matches.html", matches=all_matches)

@app.route("/update-match", methods=["POST"])
def update_match():
    if not session.get("logged_in"):
        return redirect("/login")

    match_id = request.form.get("match_id")
    match = Match.query.get(match_id)

    if match:
        match.winner = request.form.get("winner")
        match.loser = request.form.get("loser")
        match.set1_w = int(request.form.get("set1_w", 0))
        match.set1_l = int(request.form.get("set1_l", 0))
        match.set2_w = int(request.form.get("set2_w", 0))
        match.set2_l = int(request.form.get("set2_l", 0))
        match.set3_w = int(request.form.get("set3_w", 0))
        match.set3_l = int(request.form.get("set3_l", 0))
        match.date = datetime.strptime(request.form.get("date"), "%Y-%m-%d")

        match.winner_games = match.set1_w + match.set2_w + match.set3_w
        match.loser_games = match.set1_l + match.set2_l + match.set3_l

        db.session.commit()

    return redirect("/edit-matches")

@app.route("/delete-match/<int:match_id>", methods=["POST"])
def delete_match(match_id):
    if not session.get("logged_in"):
        return redirect("/login")

    match = Match.query.get(match_id)
    if match:
        db.session.delete(match)
        db.session.commit()
    return redirect("/edit-matches")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form["password"]
        if password == "rcsp4321":
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            return "Invalid admin password", 401
    return render_template("admin_login.html")

@app.route("/admin")
def admin_hq():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")
    return render_template("admin_hq.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form["password"]
        if password == "rcsp1234":
            session["logged_in"] = True
            return redirect("/")
        else:
            return "Invalid password", 401
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")

@app.route("/routes")
def show_routes():
    return "<br>".join(str(rule) for rule in app.url_map.iter_rules())


@app.route("/remove-signup", methods=["POST"])
def remove_signup():
    if not session.get("logged_in"):
        return redirect("/login")

    response_id = request.form.get("response_id")
    response = SignupResponse.query.get(response_id)
    if response:
        db.session.delete(response)
        db.session.commit()

    return redirect("/signup")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    from datetime import datetime, timedelta

    # Calculate upcoming Monday to Sunday date range
    today = datetime.utcnow().date()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    next_sunday = next_monday + timedelta(days=6)
    week_range = f"{next_monday.strftime('%m/%d')} - {next_sunday.strftime('%m/%d')}"

    if request.method == "POST":
        player = request.form.get("player")
        response = request.form.get("response")

        if player and response in ["yes", "no"]:
            new_response = SignupResponse(player=player, response=response)
            db.session.add(new_response)
            db.session.commit()
        return redirect("/signup")

    all_players = Player.query.order_by(Player.name).all()
    recent_responses = SignupResponse.query.order_by(SignupResponse.timestamp.desc()).limit(50).all()

    return render_template(
        "signup.html",
        names=[p.name for p in all_players],
        responses=recent_responses,
        week_range=week_range
    )



# Add a route and logic in main.py for the attribution page

@app.route("/attribution")
def attribution():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    all_matches = Match.query.order_by(Match.date).all()
    contributions = {}

    # Initialize contributions dict
    for match in all_matches:
        for player in [match.winner, match.loser]:
            if player not in contributions:
                contributions[player] = {
                    "matches": 0,
                    "raw_elo": 1000.0,
                    "delta_total": 0.0,
                    "decay_penalty": 0.0,
                    "confidence_adj": 0.0,
                    "final_elo": 1000.0
                }

    # Match contributions
    for match in all_matches:
        w = match.winner
        l = match.loser
        w_games = match.winner_games
        l_games = match.loser_games
        margin = w_games / max((w_games + l_games), 1)

        expected = expected_score(contributions[w]["raw_elo"], contributions[l]["raw_elo"])
        k = ACCEL_K if contributions[w]["matches"] < 3 else BASE_K
        if contributions[w]["raw_elo"] < contributions[l]["raw_elo"]:
            k *= UPSET_MULTIPLIER

        delta = k * (1 - expected) * margin

        contributions[w]["delta_total"] += delta
        contributions[l]["delta_total"] -= BASE_K * expected_score(
            contributions[l]["raw_elo"], contributions[w]["raw_elo"]
        ) * (1 - margin)

        contributions[w]["raw_elo"] += delta
        contributions[l]["raw_elo"] -= BASE_K * expected_score(
            contributions[l]["raw_elo"], contributions[w]["raw_elo"]
        ) * (1 - margin)

        contributions[w]["matches"] += 1
        contributions[l]["matches"] += 1

    # Decay effect
    league_elos = [v["raw_elo"] for v in contributions.values()]
    avg = sum(league_elos) / len(league_elos)
    std = math.sqrt(sum((e - avg) ** 2 for e in league_elos) / len(league_elos)) or 1

    for player in contributions:
        missed_matches = max(0, len(all_matches) - contributions[player]["matches"])
        decay = min(DECAY_RATE * missed_matches, std)
        contributions[player]["decay_penalty"] = -decay
        contributions[player]["raw_elo"] -= decay

    # Confidence adjustment
    avg_elo = sum(v["raw_elo"] for v in contributions.values()) / len(contributions)
    for player in contributions:
        match_count = contributions[player]["matches"]
        weight = min(1, match_count / CONFIDENCE_MATCH_CAP)
        confidence_adj = avg_elo * (1 - weight)
        contributions[player]["confidence_adj"] = -confidence_adj + avg_elo
        final = contributions[player]["raw_elo"] * weight + avg_elo * (1 - weight)
        contributions[player]["final_elo"] = final

    return render_template("attribution.html", contributions=contributions)

@app.route("/matchups")
def matchups():
    if not session.get("logged_in"):
        return redirect("/login")

    pairs, sit_out = generate_weekly_matchups(db)

    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    return render_template(
        "matchups.html",
        matchups=pairs,
        sit_out=sit_out,
        week_start=start_of_week.strftime('%B %d'),
        week_end=end_of_week.strftime('%B %d')
    )



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

@app.route("/debug-db")
def debug_db():
    return f"Using: {app.config['SQLALCHEMY_DATABASE_URI']}"
