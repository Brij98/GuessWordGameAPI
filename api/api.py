# Science Fiction Novel API - Quart Edition
#
# Adapted from "Creating Web APIs with Python and Flask"
# <https://programminghistorian.org/en/lessons/creating-apis-with-python-and-flask>.
#

from cmath import e
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
import json

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
class GameDTO:
    userId: str

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

@app.route("/insert-words", methods=["POST"])
async def insertIntoTable():
    db = await _get_db()

    wordsCnt = await db.fetch_val(
        '''
        SELECT COUNT(word) FROM Words
        '''
    )
    if wordsCnt < 2:

        try:
            inputFile = open('correct.json')
            jsonArray = json.load(inputFile)
            for word in jsonArray:
                
                i = await db.execute(
                    '''
                        INSERT INTO Words (word) VALUES (:word)
                    ''', values={"word":word}
                )  
        except:
            abort(500)
        return {"Words stored successfully": i}, 200
    else:
        return {"msg":"words already exists in the table"}, 409

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
    # hash password
    user["password"] = hash(user["password"])
    try:
        id = await db.execute("INSERT INTO Users VALUES(NULL, :username, :password)", user)
    except sqlite3.IntegrityError as e:
        abort(409, e)

    user["id"] = id
    return user, 201, { "msg": "Successfully created account" }


@app.route("/user/<string:username>/<string:password>", methods=["GET"])
async def check_password(username: str, password: str):
    db = await _get_db()

    try:
        user = await db.fetch_one(
            "SELECT * FROM Users WHERE username = :username",
            values={ "username": username })
    except Exception as e:
        print(e)
        abort(400)

    return {"authenticated": hash(password) == user.password}, 200

@app.route("/game", methods=["POST"])
@validate_request(UserDTO)
async def create_game(data: UserDTO):
    db = await _get_db()
    user = dataclasses.asdict(data)

    f = open('correct.json')
    words = json.load(f)
    f.close()
    word = words[random.randrange(len(words))]

    try:
        id = await db.execute("INSERT INTO Games VALUES (NULL, :userId :word, NULL, NULL)", 
            values={ 'word': word, 'userId': user['userId'] })
    except Exception as e:
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
