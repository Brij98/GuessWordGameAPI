import dataclasses
from functools import wraps
from multiprocessing.connection import wait
import sqlite3
from quart import Quart, request, g, abort
from quart_schema import QuartSchema, validate_request

import databases
import toml



app = Quart(__name__)
QuartSchema(app)

app.config.from_file(f"./etc/Project1.toml", toml.load)


@dataclasses.dataclass
class UserDataClass:
    username: str
    password: str


async def _get_db():
    db = getattr(g, "_sqlite_db", None)
    if db is None:
        db = g._sqlite_db = databases.Database(app.config["DATABASES"]["URL"])
        await db.connect()
    return db

async def getUserById(username: str):
    db = await _get_db()
    

def auth_required(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        db = await _get_db()
        auth = request.authorization
        # auth = request.headers.get('Authorization')
        # print("**********auth*********:", auth)  # debug
        if auth is not None:
            user = await db.fetch_one("SELECT * FROM Users WHERE username = :username AND password = :password",
                          values={"username": auth.username, "password": auth.password})

            # print("**********User*********:", user)  # debug
            if(user is not None):
                return await f(*args, **kwargs)
            else:
                return {"error": "Valid Authorization is required"}, 401
        else:
            return {"error": "Authorization is required"}, 401
        return await f(*args, **kwargs)
    return wrapper

@app.route("/", methods=["GET"])
async def index():
    return "Hello World", 200

# Httpie Request -> http GET 127.0.0.1:5000/basic-auth -a Pam:pam01
@app.route("/basic-auth", methods=["GET"])
@auth_required
async def basicAuth():
    return {"authenticated": "true"}, 200
   
# Httpie Request -> http POST 127.0.0.1:5000/register-user username=Tommy password=007
@app.route("/register-user", methods=["POST"])
@validate_request(UserDataClass)
async def registerUser(data: UserDataClass):
    db = await _get_db()
    # requestData = await request.get_json()
    # print("**********requestData**************:", data)  # debug
    try:
        id = await db.execute(
            """        
        INSERT INTO USERS (username, password) VALUES(:username, :password)
        """, 
        # values={"username": requestData['username'],
                    #  "password": requestData['password']})
        values={"username": data.username,
             "password": data.password})                    
    except sqlite3.IntegrityError as e:
        abort(409, e)

    return "Registered Successfully", 200
