# tennis_ladder/matchmaking.py
from datetime import datetime, timedelta, time
from models import Match, SignupResponse, Player
from sqlalchemy.orm import joinedload
from elo import calculate_elo

def get_current_week_range():
    now = datetime.utcnow()
    eastern_cutoff = datetime.combine(now.date(), time(23, 0)) - timedelta(days=now.weekday())  # Sunday 7 PM ET -> 11 PM UTC
    if now < eastern_cutoff:
        # Show current week (Monday to Sunday of this week)
        start = now.date() - timedelta(days=now.weekday())
    else:
        # After Sunday 7 PM ET, show next week
        start = now.date() - timedelta(days=now.weekday() - 7)
    end = start + timedelta(days=6)
    return start, end

def generate_weekly_matchups(db):
    start, end = get_current_week_range()

    # Get latest response per player (one per week)
    responses = (db.session.query(SignupResponse)
                 .filter(SignupResponse.timestamp >= start)
                 .order_by(SignupResponse.timestamp.desc())
                 .all())

    latest = {}
    for r in responses:
        if r.player not in latest:
            latest[r.player] = r

    signed_up = [r.player for r in latest.values() if r.response == 'yes']

    if len(signed_up) < 2:
        return [], None  # Not enough for matches

    signed_up.sort(key=lambda p: latest[p].timestamp)  # Sort by signup time
    odd_player = signed_up[-1] if len(signed_up) % 2 == 1 else None
    eligible = signed_up[:-1] if odd_player else signed_up

    # Get Elo rankings, defaulting to 1000 for players not in list
    elo_ratings = {name: elo for name, elo, _, _ in calculate_elo()}
    rankings = {player: elo_ratings.get(player, 1000) for player in eligible}

    eligible.sort(key=lambda p: rankings.get(p, 1000))  # Sort by Elo

    # Get last opponents
    last_opponent = {}
    last_matches = (Match.query.order_by(Match.date.desc()).all())
    for match in last_matches:
        for a, b in [(match.winner, match.loser), (match.loser, match.winner)]:
            if a not in last_opponent:
                last_opponent[a] = b
        if len(last_opponent) >= len(eligible):
            break

    used = set()
    matchups = []
    for i, player in enumerate(eligible):
        if player in used:
            continue
        for j in range(i + 1, len(eligible)):
            partner = eligible[j]
            if partner in used:
                continue
            if last_opponent.get(player) != partner:
                matchups.append((player, partner))
                used.add(player)
                used.add(partner)
                break

    print("Signed up players:", signed_up)
    print("Rankings available for:", rankings)
    print("Eligible after filtering:", eligible)

    return matchups, odd_player
