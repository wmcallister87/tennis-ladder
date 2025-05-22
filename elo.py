# elo.py
from models import Match
import math
from datetime import datetime

BASE_K = 32
ACCEL_K = 40
UPSET_MULTIPLIER = 1.2
CONFIDENCE_MATCH_CAP = 2
RECENCY_LAMBDA = 0.05
DECAY_RATE = 0.5
DECAY_DELAY_DAYS = 28

def expected_score(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))

def normalize_elos(players):
    elos = [p["elo"] for p in players.values()]
    mean = sum(elos) / len(elos)
    std = math.sqrt(sum((e - mean) ** 2 for e in elos) / len(elos)) or 1
    for p in players:
        players[p]["elo"] = 1000 + ((players[p]["elo"] - mean) / std) * 100
    return players

def calculate_elo():
    players = {}
    last_match_date = {}
    win_counts = {}
    all_matches = Match.query.order_by(Match.date).all()
    match_count = len(all_matches)

    for idx, match in enumerate(all_matches):
        winner = match.winner
        loser = match.loser
        w_games = match.winner_games
        l_games = match.loser_games
        total_games = max(w_games + l_games, 1)
        margin = w_games / total_games
        recency_weight = math.exp(-RECENCY_LAMBDA * (match_count - idx))

        for player in [winner, loser]:
            if player not in players:
                players[player] = {"elo": 1000, "matches": 0}
            if player not in win_counts:
                win_counts[player] = 0

        winner_elo = players[winner]["elo"]
        loser_elo = players[loser]["elo"]
        expected_win = expected_score(winner_elo, loser_elo)

        k = ACCEL_K if players[winner]["matches"] < 3 else BASE_K
        if winner_elo < loser_elo:
            k *= UPSET_MULTIPLIER

        delta = k * (1 - expected_win) * margin * recency_weight
        players[winner]["elo"] += delta
        players[loser]["elo"] -= BASE_K * expected_score(loser_elo, winner_elo) * (1 - margin) * recency_weight

        players[winner]["matches"] += 1
        players[loser]["matches"] += 1

        win_counts[winner] += 1
        last_match_date[winner] = match.date
        last_match_date[loser] = match.date

    today = datetime.utcnow()
    for p in players:
        last_date = last_match_date.get(p)
        if last_date:
            days_inactive = (today - last_date).days
            if days_inactive > DECAY_DELAY_DAYS:
                decay = DECAY_RATE * (days_inactive - DECAY_DELAY_DAYS)
                players[p]["elo"] -= decay

    if not players:
        return []

    league_avg = sum(p["elo"] for p in players.values()) / len(players)
    for p in players:
        m = players[p]["matches"]
        weight = min(1, m / CONFIDENCE_MATCH_CAP)
        players[p]["elo"] = players[p]["elo"] * weight + league_avg * (1 - weight)

    players = normalize_elos(players)

    return sorted([
        (
            name,
            round(info["elo"], 2),
            info["matches"],
            round(win_counts.get(name, 0) / info["matches"], 2) if info["matches"] > 0 else 0.0
        ) for name, info in players.items()
    ], key=lambda x: x[1], reverse=True)

