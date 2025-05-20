import sqlite3
import pandas as pd

# Connect to local SQLite file
conn = sqlite3.connect("ladder.db")

# Read tables into DataFrames
players_df = pd.read_sql_query("SELECT * FROM player", conn)
matches_df = pd.read_sql_query("SELECT * FROM match", conn)

conn.close()

# Preview
print(players_df.head())
print(matches_df.head())
