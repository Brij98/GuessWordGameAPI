import base64
import hashlib
import secrets

def create_hint(guess: str, word: str) -> str:
    if guess == word:
        return 'You win!'

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


# Credit to: https://til.simonwillison.net/python/password-hashing-with-pbkdf2 for hashing stuff
ALGORITHM = "pbkdf2_sha256"


def hash_password(password, salt=None, iterations=260000):
    if salt is None:
        salt = secrets.token_hex(16)
    assert salt and isinstance(salt, str) and "$" not in salt
    assert isinstance(password, str)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    b64_hash = base64.b64encode(pw_hash).decode("ascii").strip()
    return "{}${}${}${}".format(ALGORITHM, iterations, salt, b64_hash)


def verify_password(password, password_hash):
    if (password_hash or "").count("$") != 3:
        return False
    algorithm, iterations, salt, b64_hash = password_hash.split("$", 3)
    iterations = int(iterations)
    assert algorithm == ALGORITHM
    compare_hash = hash_password(password, salt, iterations)
    return secrets.compare_digest(password_hash, compare_hash)

