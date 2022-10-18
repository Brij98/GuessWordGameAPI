# Science Fiction Novel API - Quart Edition
#
# Adapted from "Creating Web APIs with Python and Flask"
# <https://programminghistorian.org/en/lessons/creating-apis-with-python-and-flask>.
#

from code import interact
import collections
import dataclasses
from functools import wraps
import sqlite3
import textwrap
from typing import List

import databases
import toml

from quart import Quart, g, request, abort
from quart_schema import QuartSchema, RequestSchemaValidationError, validate_request

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
class Word:
    word: str


@dataclasses.dataclass
class Session:
    sessionId: int
    userId: int
    word: str
    movesCompleted: str
    sessionCompleted: bool


@dataclasses.dataclass
class Guess:
    sessionId: int
    guessNo: int
    guess: str
    hint: str


@dataclasses.dataclass
class GuessDTO


sessionId: int
guess: str


# Database connections on demand
#   See <https://flask.palletsprojects.com/en/2.2.x/patterns/sqlite3/>
#   and <https://www.encode.io/databases/connections_and_transactions/>


async def _get_db():
    db = getattr(g, "_sqlite_db", None)
    if db is None:
        db = g._sqlite_db = databases.Database(app.config["DATABASES"]["URL"])
        await db.connect()
    return db


@app.route("/user", methods=["POST"])
@validate_request(UserDTO)
async def create_user(data):
    db = await _get_db()
    # turn input into dict
    user = dataclasses.asdict(data)
    # hash password
    user["password"] = hash(user["password"])
    try:
        id = await db.execute("INSERT INTO Users VALUES(:username, :password)", user)
    except sqlite3.IntegrityError as e:
        abort(409, e)

    user["id"] = id
    return book, 201, {"msg": "Successfully created account"}


@app.route("/user/(str:username)/(str:password)", methods=["GET"])
async def check_password(username: str, password: str):
    db = await _get_db()

    try:
        user = await db.fetch_one(
            "SELECT * FROM User WHERE username = :username",
            values={"username": username})
    except:
        abort(404)

    return 200, {"authenticated", hash(password) == user.password}


@auth_required
@app.route("/session", methods=["POST"])
async def create_session(data):
    pass


@auth_required
@app.route("/guess/(int:sessionId)/(str:guess)")
async def guess(sessionId: int, guess: str):
    pass


@app.route("/books/<int:id>", methods=["GET"])
async def one_book(id):
    db = await _get_db()
    book = await db.fetch_one("SELECT * FROM books WHERE id = :id", values={"id": id})
    if book:
        return dict(book)
    else:
        abort(404)


def auth_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        auth = request.authorization
        db = _get_db()
        user = await db.fetch_one(
            "SELECT * FROM User WHERE username = :username",
            values={"username": auth.username})

        if (
            auth is not None and
            auth.type == "basic" and
            auth.username == user.username and
            hash(auth.password) == user.password
        ):
            return await func(*args, **kwargs)
        else:
            abort(401)

    return wrapper


def create_hint(guess: str, word: str) -> str:
    if guess == word:
        return 'Guess is correct!'

    if len(guess) != 5:
        return 'Invalid guess!'

    guess, word = guess.upper(), word.upper()
    guessSet, wordSet = set(guess), set(word)
    difference = guessSet.difference(wordSet)
    states = []

    # 2 is same pos, 1 is wrong pos, 0 is not in word
    # create array that has state for each char
    for i in range(5):
        if guess[i] == word[i]:
            states.append(2)
            continue

        if guess[i] in wordSet:
            states.append(1)
            continue

        states.append(0)

    hint = []

    for i, state in enumerate(states):
        char = guess[i]
        if state == 2 and char in guessSet:
            hint.append(f"{guess[i]} in {i + 1},")
            guessSet.remove(guess[i])
        elif state == 1 and char in guessSet:
            hint.append(f"{guess[i]} not in {i + 1},")
            guessSet.remove(guess[i])

    # add hints for chars not in word
    for char in difference:
        hint.append(char)

    if len(difference):
        hint.append("not in word")
    else:
        hint[-1] = hint[-1][:-1]

    return " ".join(hint)
