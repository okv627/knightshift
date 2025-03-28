import os
import re
import sys
import time
import json
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    String,
    MetaData,
    update,
    select,
    Boolean,
    Integer,
    Date,
    Time,
    text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from db_utils import load_db_credentials, get_database_url, get_lichess_token

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env.local")

creds = load_db_credentials()
DATABASE_URL = get_database_url(creds)

engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
metadata = MetaData()

tv_channel_games_table = Table(
    "tv_channel_games",
    metadata,
    Column("id", String, primary_key=True),
    Column("moves", String),
    Column("updated", Boolean, default=False),
    Column("result", String),
    Column("termination", String),
    Column("utc_date", Date),
    Column("utc_time", Time),
    Column("white_elo", Integer),
    Column("black_elo", Integer),
    Column("variant", String),
    Column("time_control", String),
    Column("eco", String),
    Column("opening", String)
)

Session = sessionmaker(bind=engine)
session = Session()


def fetch_game_moves(game_id):
    url = f"https://lichess.org/game/export/{game_id}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {get_lichess_token()}",
    }
    response = requests.get(url, headers=headers)

    # Check if response is OK
    if response.status_code == 200:
        pgn_text = response.text

        # Parse the PGN headers to get game data
        game_data = parse_game_data_from_pgn(pgn_text)

        # Extract the moves
        moves = extract_moves_from_pgn(pgn_text)

        return moves, game_data
    else:
        print(
            f"Failed to fetch moves for game {game_id}: {response.status_code}, {response.text}"
        )
        return None, None


def parse_game_data_from_pgn(pgn_text):
    game_data = {}

    # Use regex to extract the relevant PGN headers
    headers = {
        "result": r"\[Result\s\"([^\"]+)\"",
        "termination": r"\[Termination\s\"([^\"]+)\"",
        "utc_date": r"\[UTCDate\s\"([^\"]+)\"",
        "utc_time": r"\[UTCTime\s\"([^\"]+)\"",
        "white_elo": r"\[WhiteElo\s\"([^\"]+)\"",
        "black_elo": r"\[BlackElo\s\"([^\"]+)\"",
        "variant": r"\[Variant\s\"([^\"]+)\"",
        "time_control": r"\[TimeControl\s\"([^\"]+)\"",
        "eco": r"\[ECO\s\"([^\"]+)\"",
        "opening": r"\[Opening\s\"([^\"]+)\"",
    }

    for field, regex in headers.items():
        match = re.search(regex, pgn_text)
        if match:
            game_data[field] = match.group(1)

    return game_data


def extract_moves_from_pgn(pgn_text):
    moves_section = False
    moves = []
    for line in pgn_text.splitlines():
        if not line.startswith("[") and line.strip():
            moves_section = True
        if moves_section:
            line = re.sub(r"\{[^}]*\}", "", line).strip()
            moves.append(line)
    return " ".join(moves)


def update_game_record(game_id, moves, game_data):
    # Handle Elo fields with "?" by converting them to None
    white_elo = None if game_data["white_elo"] == "?" else int(game_data["white_elo"])
    black_elo = None if game_data["black_elo"] == "?" else int(game_data["black_elo"])

    session.execute(
        update(tv_channel_games_table)
        .where(tv_channel_games_table.c.id == game_id)
        .values(
            moves=moves,
            result=game_data["result"],
            termination=game_data["termination"],
            utc_date=game_data["utc_date"],
            utc_time=game_data["utc_time"],
            white_elo=white_elo,
            black_elo=black_elo,
            variant=game_data["variant"],
            time_control=game_data["time_control"],
            eco=game_data["eco"],
            opening=game_data["opening"],
        )
    )

    # Set 'updated=True' if the game is finished (i.e., result is not '*' and termination is not 'Unterminated')
    if game_data["result"] != "*" and game_data["termination"] != "Unterminated":
        session.execute(
            update(tv_channel_games_table)
            .where(tv_channel_games_table.c.id == game_id)
            .values(updated=True)  # Mark as updated
        )

    try:
        session.commit()
    except Exception as e:
        print(f"Error during commit: {e}")
        session.rollback()  # Rollback in case of error


def run_update_pass():
    batch_size = 1000
    total_updated = 0
    total_failed = 0
    start_time = time.time()

    # Fetch all games where termination is 'Unterminated' or result is '*', and updated is False
    games = session.execute(
        select(tv_channel_games_table).where(
            (
                (tv_channel_games_table.c.termination == "Unterminated")
                | (tv_channel_games_table.c.result == "*")
            )
            & (
                tv_channel_games_table.c.updated == False
            )  # Only fetch rows where updated is False
        )
    ).fetchall()

    num_games = len(games)
    print(f"Fetched {num_games} games to update.")  # Debug log

    if num_games == 0:
        print("No games found to update.")
        return

    # Estimate time for completion
    estimated_time_sec = num_games * 0.5  # assuming each game takes ~0.5 seconds
    estimated_time_min = estimated_time_sec // 60  # Whole minutes
    estimated_time_rem_sec = estimated_time_sec % 60  # Remaining seconds

    # Print human-readable estimated time
    if estimated_time_min == 0:
        print(f"Estimated time to process: {int(estimated_time_rem_sec)} seconds.")
    else:
        print(
            f"Estimated time to process: {int(estimated_time_min)} minutes {int(estimated_time_rem_sec)} seconds."
        )

    last_report_time = time.time()

    for idx, game in enumerate(games):
        game_id = game.id

        # Fetch both moves and game data
        moves, game_data = fetch_game_moves(game_id)

        if game_data:  # If game data is found, update the record
            try:
                if moves:
                    update_game_record(game_id, moves, game_data)
                    total_updated += 1
                else:
                    total_failed += 1
            except HTTPError as e:
                if e.response.status_code == 429:
                    print("Rate limit hit. Exiting program.")
                    sys.exit(1)
                else:
                    raise

        # Periodic update every 30 seconds
        if time.time() - last_report_time >= 30:
            elapsed_time = time.time() - start_time
            processed = total_updated + total_failed
            remaining = num_games - processed
            estimated_remaining_sec = remaining * 0.65
            estimated_remaining_min = estimated_remaining_sec // 60  # Whole minutes
            estimated_remaining_rem_sec = estimated_remaining_sec % 60  # Remaining seconds

            print(f"Processed {processed}/{num_games} games. "
                f"Remaining: {remaining}. Estimated time remaining: {int(estimated_remaining_min)} minutes {int(estimated_remaining_rem_sec)} seconds.")
            last_report_time = time.time()

        # Minimal pause to avoid hitting rate limits
        time.sleep(0.5)

    # Final completion message
    print("Update process completed successfully.")

if __name__ == "__main__":
    run_update_pass()
