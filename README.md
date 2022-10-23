# CPSC 449: Project 1


## Team Members

- Charlie Taylor
- Clay Golan
- Sreevidya Sreekantham
- Brijesh Prajapati


## Starting and Initialization

run from /api directory

```bash
rm ./var/api.db
sqlite3 ./var/api.db < ./share/api.sql
python3 populate_db.py
foreman start
```

## Documentation

located at localhost:5000/docs

`GET /user` uses basic auth to check if your pasword is correct.

`GET /game/user` returns all games in progress for a given user.

`POST /game` creates new game linked to provided userId in boy.