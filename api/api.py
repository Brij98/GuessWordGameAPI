# Science Fiction Novel API - Quart Edition
#
# Adapted from "Creating Web APIs with Python and Flask"
# <https://programminghistorian.org/en/lessons/creating-apis-with-python-and-flask>.
#

from code import interact
import collections
import dataclasses
from functools import wraps
import json
import random
import sqlite3
import textwrap
from typing import List

import databases
import toml

from quart import Quart, g, request, abort
from quart_schema import QuartSchema, RequestSchemaValidationError, validate_request

from utils import create_hint

app = Quart(__name__)
QuartSchema(app)

app.config.from_file(f"./etc/{__name__}.toml", toml.load)


@dataclasses.dataclass
class User:
    userId: int
    username: str
    password: str


@dataclasses.dataclass
class UserDTO:
    username: str
    password: str


@dataclasses.dataclass
class Game:
    gameId: int
    userId: int
    word: str
    movesCompleted: str
    gameCompleted: bool


@dataclasses.dataclass
class Guess:
    gameId: int
    guessNo: int
    guess: str
    hint: str


# Database connections on demand
#   See <https://flask.palletsprojects.com/en/2.2.x/patterns/sqlite3/>
#   and <https://www.encode.io/databases/connections_and_transactions/>


async def _get_db():
    db = getattr(g, "_sqlite_db", None)
    if db is None:
        db = g._sqlite_db = databases.Database(app.config["DATABASES"]["URL"])
        await db.connect()
    return db

@app.teardown_appcontext
async def close_connection(exception):
    db = getattr(g, "_sqlite_db", None)
    if db is not None:
        await db.disconnect()


@app.route("/", methods=["GET"])
def index():
    return textwrap.dedent(
        """
        <h1>Word Guessing Game</h1>
        <p>A prototype for definitely not Wordle.</p>\n
        """
    )


@app.route("/user", methods=["POST"])
@validate_request(UserDTO)
async def create_user(data: UserDTO):
    db = await _get_db()
    user = dataclasses.asdict(data)
    print(user)
    # hash password
    user["password"] = hash(user["password"])
    try:
        id = await db.execute("INSERT INTO Users VALUES(NULL, :username, :password)", user)
    except sqlite3.IntegrityError as e:
        abort(409, e)

    user["id"] = id
    return user, 201, { "msg": "Successfully created account" }


@app.route("/user/(str:username)/(str:password)", methods=["GET"])
async def check_password(username: str, password: str):
    db = await _get_db()

    try:
        user = await db.fetch_one(
            "SELECT * FROM Users WHERE username = :username",
            values={ "username": username })
    except:
        abort(404)

    return 200, {"authenticated": hash(password) == user.password}


@app.route("/game", methods=["POST"])
async def create_game():
    db = await _get_db()
    f = open('correct.json')
    words = json.load(f)
    f.close()
    word = words[random.randrange(len(words))]

    try:
        id = await db.execute("INSERT INTO Games VALUES (NULL, :word, NULL, NULL)", { 'word': word })
    except Exception as e:
        print(str(e))
        abort(400)
    
    return { 'id': id }, 201, { "msg": "Successfully created game" }



@app.route("/guess/<int:gameId>/<string:guess>", methods=["GET"])
async def guess(gameId: int, guess: str):
    db = await _get_db()

    try:
        game = await db.fetch_one(
            "SELECT * FROM Games WHERE GameId = :gameId",
            values={ "gameId": gameId })
        # game = dataclasses.dataclass(game)
        print(game)
    except:
        abort(400)

    return 200, { 'msg': create_hint(guess, game["word"]) }
