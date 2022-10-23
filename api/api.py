# Science Fiction Novel API - Quart Edition
#
# Adapted from "Creating Web APIs with Python and Flask"
# <https://programminghistorian.org/en/lessons/creating-apis-with-python-and-flask>.
#

from code import interact
import collections
import dataclasses
import json
import random
import sqlite3
import textwrap

import databases
import toml

from quart import Quart, g, request, abort
from quart_schema import QuartSchema, RequestSchemaValidationError, validate_request

from utils import create_hint, hash_password, verify_password

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
class GetGameDTO:
    gameId: str


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
    # hash password
    user["password"] = hash_password(user["password"])
    try:
        id = await db.execute("INSERT INTO Users VALUES(NULL, :username, :password)", user)
    except sqlite3.IntegrityError as e:
        abort(409, e)

    user["id"] = id
    return user, 201, {"msg": "Successfully created account"}


@app.route("/user/<string:username>/<string:password>", methods=["GET"])
async def check_password(username: str, password: str):
    db = await _get_db()

    try:
        (userId, dbUsername, dbPassword) = await db.fetch_one(
            "SELECT * FROM Users WHERE username = :username",
            values={"username": username})
        print(dbPassword)
    except Exception as e:
        print(e)
        abort(400)

    return {"authenticated": verify_password(password, dbPassword)}, 200


@app.route("/game", methods=["POST"])
@validate_request(GameDTO)
async def create_game(data: GameDTO):
    db = await _get_db()
    user = dataclasses.asdict(data)

    try:
        word = await db.fetch_one("SELECT Word FROM Words WHERE Correct = 1 ORDER BY RANDOM()")
        print(word)
        id = await db.execute("INSERT INTO Games VALUES(NULL, :userId, :word, 0, 0)",
                              values={'word': word, 'userId': int(user['userId'])})
    except Exception as e:
        print(e)
        abort(400)

    return {'id': id, "msg": "Successfully created game"}, 201


@app.route("/game/<int:id>", methods=["GET"])
async def get_game(id: int):
    db = await _get_db()
    try:
        (id, userId, word, moves, completed) = await db.fetch_one(
            "SELECT * FROM Games WHERE GameId = :gameId",
            values={'gameId': id})

        results = await db.fetch_all("SELECT * FROM Guesses WHERE GameId = :gameId",
                                     values={'gameId': id})
        
        guesses = []
        for result in results:
            (id, gameId, guess, hint) = result
            guesses.append({'id': id, 'GameId': gameId, 'guess': guess, 'hint': hint})

        return {'game': {'id': id, 'userId': userId, 'moves': moves, 'completed': bool(completed)},
                'guesses': guesses}, 200
    except Exception as e:
        print(e)
        abort(400)


@app.route("/game", methods=["GET"])
async def get_games():
    db = await _get_db()
    userId = request.args.get("userId")
    print(userId)
    try:
        results = await db.fetch_all(
            "SELECT * FROM Games WHERE UserId = :userId",
            values={"userId": userId})
        print(results)
        games = []
        for result in results:
            (id, userId, word, moves, completed) = result
            games.append({'id': id, 'userId': userId, 'moves': moves, 'completed': bool(completed)})

        return games, 200
    except:
        abort(400)


@app.route("/guess/<int:gameId>/<string:guess>", methods=["GET"])
async def guess(gameId: int, guess: str):
    db = await _get_db()

    try:
        (id, userId, word, moves, completed) = await db.fetch_one(
            "SELECT * FROM Games WHERE GameId = :gameId",
            values={"gameId": gameId})

        if completed:
            return {'msg': 'Game already completed!'}, 200

        hint = create_hint(guess, word)

        if guess == word:
            moves += 1
            completed = 1

            await db.execute("INSERT INTO Guesses VALUES(NULL, :gameId, :guess, :hint)",
                             values={'gameId': id, 'guess': guess, 'hint': hint})

            await db.execute(
                """
                UPDATE Games SET MovesCompleted = :moves, GameCompleted = :completed
                WHERE GameId = :gameId
                """,
                values={'moves': moves, 'completed': completed, 'gameId': id})
            return {'msg': hint}, 200

        if await is_valid_guess(guess):
            moves += 1
            

            await db.execute("INSERT INTO Guesses VALUES(NULL, :gameId, :guess, :hint)",
                             values={'gameId': id, 'guess': guess, 'hint': hint})

            if moves >= 6:
                completed = 1

            await db.execute(
                """
                UPDATE Games SET MovesCompleted = :moves, GameCompleted = :completed
                WHERE GameId = :gameId
                """,
                values={'moves': moves, 'completed': completed, 'gameId': id})

            return {'msg': hint}, 200

    except Exception as e:
        print(e)
        abort(400)

    return {'msg': 'Invalid guess, please try again'}, 200


async def is_valid_guess(guess: str):
    db = await _get_db()
    words = await db.fetch_all("SELECT * FROM Words WHERE Word = :guess", values={'guess': guess})

    return len(words) > 0
