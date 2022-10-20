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
# @validate_request(UserDTO)
async def create_user(data: UserDTO):
    db = await _get_db()
    # turn input into dict
    user = dataclasses.asdict(data)
    # hash password
    user["password"] = hash(user["password"])
    print("pasword hashed")
    try:
        id = await db.execute("INSERT INTO Users VALUES(:username, :password)", user)
    except sqlite3.IntegrityError as e:
        abort(409, e)

    user["id"] = id
    return user, 201, {"msg": "Successfully created account"}


@app.route("/user/(str:username)/(str:password)", methods=["GET"])
async def check_password(username: str, password: str):
    db = await _get_db()

    try:
        user = await db.fetch_one(
            "SELECT * FROM User WHERE username = :username",
            values={ "username": username })
    except:
        abort(404)

    return 200, {"authenticated": hash(password) == user.password}


@app.route("/session", methods=["POST"])
async def create_session(data):
    db = await _get_db()

    try:
        word = await db.fetch_one('SELECT * FROM Word ORDER BY RANDOM() LIMIT 1;')

        await db.execute("""
        INSERT INTO Sessions VALUES
        (:userId, :word, 0, 0)
        """, { 'userId': data.userId, 'word': word })
    except:
        abort(400)
    
    return 200, { "status": "Session created" }
    


@app.route("/guess/(int:sessionId)/(str:guess)")
async def guess(sessionId: int, guess: str):
    db = await _get_db()

    try:
        session = await db.fetch_one(
            "SELECT * FROM Session where SessionID = :sessionId", sessionId)
    except:
        abort(404)

    session = dataclasses.dataclass(session)

    return 200, create_hint(guess, session.word)



@dataclasses.dataclass
class Book:
    published: int
    author: str
    title: str
    first_sentence: str


@app.route("/books/", methods=["POST"])
@validate_request(Book)
async def create_book(data):
    db = await _get_db()
    book = dataclasses.asdict(data)
    try:
        id = await db.execute(
            """
            INSERT INTO books(published, author, title, first_sentence)
            VALUES(:published, :author, :title, :first_sentence)
            """,
            book,
        )
    except sqlite3.IntegrityError as e:
        abort(409, e)

    book["id"] = id
    return book, 201, {"Location": f"/books/{id}"}

