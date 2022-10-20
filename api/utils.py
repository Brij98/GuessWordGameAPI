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


