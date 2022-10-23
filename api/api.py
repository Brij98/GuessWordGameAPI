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
    user["password"] = hash(user["password"])
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
        user: User = await db.fetch_one(
            "SELECT * FROM Users WHERE username = :username",
            values={"username": username})
    except Exception as e:
        print(e)
        abort(400)

    return 200, {"authenticated": hash(password) == user.password}


@app.route("/game", methods=["POST"])
@validate_request(UserDTO)
async def create_game(data: UserDTO):
    db = await _get_db()
    user = dataclasses.asdict(data)

    f = open('correct.json')
    words = json.load(f)
    f.close()
    word = words[random.randrange(len(words))]
    print(data)
    print(user)
    try:
        id = await db.execute("INSERT INTO Games VALUES (NULL, :userId :word, NULL, NULL)",
                              values={'word': word, 'userId': user['userId']})
    except Exception as e:
        print(e)
        abort(400)

    return {'id': id}, 201, {"msg": "Successfully created game"}


@app.route("/game/<int:id>", methods=["GET"])
@validate_request(GetGameDTO)
async def get_game(data: GetGameDTO):
    db = await _get_db()

    try:
        game = await db.execute("SELECT * FROM Games WHERE GameId = :gameId",
                                values={'gameId': data.gameId})

        guesses = await db.fetch_all("SELECT * FROM Guesses WHERE GameId = :gameId",
                                     values={'gameId': data.gameId})

        return 200, {'game': game, 'guesses': guesses}
    except:
        abort(400)


@app.route("/game", methods=["GET"])
@validate_request(GetGameDTO)
async def get_games():
    db = await _get_db()
    userId = request.args.get("userId")

    try:
        games = await db.fetch_all(
            "SELECT * FROM Games WHERE UserId = :userId",
            values={"userId": userId})

        for i in range(len(games)):
            games[i]["Word"] = ""

        return 200, games
    except:
        abort(400)


@app.route("/guess/<int:gameId>/<string:guess>", methods=["GET"])
async def guess(gameId: int, guess: str):
    db = await _get_db()

    try:
        game: Game = await db.fetch_one(
            "SELECT * FROM Games WHERE GameId = :gameId",
            values={"gameId": gameId})

        if game.gameCompleted:
            return 200, {'msg': 'Game already completed!'}

        if guess == game.word:
            game.movesCompleted += 1
            game.gameCompleted = 1
            await db.execute(
                """
                UPDATE Games SET MovesCompleted = :moves, GameCompleted = :completed
                WHERE GameId = :gameId
                """,
                values={'moves': game.movesCompleted, 'completed': game.gameCompleted, 'gameId': game.gameId})
            return 200, {'msg': 'You win!'}

        if await is_valid_guess(guess):
            game.movesCompleted += 1
            hint = create_hint(guess, game.word)

            await db.execute("INSERT INTO Gueses VALUES(NULL, :gameId, :guess, :hint)",
                             values={'gameId': game.gameId, 'guess': guess, 'hint': hint})

            if game.movesCompleted >= 6:
                game.gameCompleted = 1

            await db.execute(
                """
                UPDATE Games SET MovesCompleted = :moves, GameCompleted = :completed
                WHERE GameId = :gameId
                """,
                values={'moves': game.movesCompleted, 'completed': game.gameCompleted, 'gameId': game.gameId})

            return 200, {'msg', hint}

    except:
        abort(400)

    return 200, {'msg': 'Invalid guess, please try again'}


async def is_valid_guess(guess: str):
    db = _get_db()
    words = await db.fetch_all("SELECT * FROM Words WHERE Word = :guess", values={'guess': guess})

    return len(words) > 0
