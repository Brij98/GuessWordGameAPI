import json
import sqlite3

def insert_words(cursor: sqlite3.Cursor):
  with open("./valid.json") as f:
    validJson = json.load(f)

  for word in validJson:
    cursor.execute("INSERT INTO Words VALUES(?, 0)", (word,))

  with open("./correct.json") as f:
    correctJson = json.load(f)
  
  for word in correctJson:
    cursor.execute("INSERT INTO Words VALUES(?, 1)", (word,))

if __name__ == "__main__":
  connect = sqlite3.connect("./var/api.db")
  cur = connect.cursor()
  insert_words(cur)
  connect.commit()
