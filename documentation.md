**Image Prompt Guessing Game Bot**

**Brainstorming**
redirect users from bot DM to the main group
command to start game in group
prevent concurrent games (block new games if one is active)
join phase: 30-second countdown (updates every 1 sec)
live update of joined players count
challenge phase: post an image to the group
redirect players to bot DM to submit guesses privately
allow only joined players to guess
enforce one guess per player limit
guess phase: 30-second countdown (updates every 1 sec)
scoring: use semantic similarity to grade guesses against the original image prompt
image generation: generate an image for each player's submitted prompt
results: display winner, grades, and generated images in the group

**Version 1: Group Setup & Game Lobby**
[1.1] /start command in DM redirects to group
[1.2] /start_game in group initiates game lobby
[1.3] join button with live 30s countdown and player count
[1.4] game state management (block concurrent /start_game requests)

**Version 2: Challenge & Private Guessing**
[2.1] display challenge image in group when lobby timer ends
[2.2] provide a deep-link button to redirect joined players to DM
[2.3] accept guesses in DM (validate player joined & hasn't guessed yet)
[2.4] guess phase 30s countdown timer in group

**Version 3: Evaluation & Results**
[3.1] evaluate prompt guesses using semantic similarity API
[3.2] generate images based on player prompts using image generation API
[3.3] announce winner, grades, and display all generated images in the group

**User stories**

Alice finds the bot and wants to play. She opens the bot's private DM and types:

> /start
> Welcome to the game bot! Please join our official group to play: [Group Link]

Alice goes to the group. She wants to start a game.

> /start_game

<Bot posts a message that updates every second>
🎮 **New Game Starting!**
Time to join: 30s
Players joined: 0
[ Join Game ]

Bob clicks the [Join Game] button. The bot edits the message:
🎮 **New Game Starting!**
Time to join: 29s
Players joined: 1
[ Join Game ]

Charlie enters the group and tries to start another game while the lobby is open.

> /start_game
> You cannot start a game right now. Please wait until the current game finishes.

The 30-second join timer reaches 0. No one else can join. The bot posts the challenge:
<Bot posts a generated/selected challenge image>
🖼️ **Describe this image!**
Alice, Bob, you have 30 seconds to submit your prompt!
Time remaining: 30s (updates every 1s)
[ Submit Guess Privately ]

Bob clicks the button, which takes him to the bot's private DM.

> "A futuristic city at sunset with flying cars"
> Guess received! Waiting for other players...

Bob tries to send another guess just in case.

> "A cyberpunk city"
> You can't send multiple prompts. Your first guess is locked in.

The 30-second guessing timer in the group reaches 0. The bot processes the results and posts them in the group:
🏆 **Game Over! Here are the results:**

🥇 **Winner:** Bob
Grade: 92% match
Prompt: "A futuristic city at sunset with flying cars"
<Bot posts the image generated from Bob's prompt>

🥈 **Runner up:** Alice
Grade: 75% match
Prompt: "Tall buildings and a red sky"
<Bot posts the image generated from Alice's prompt>
