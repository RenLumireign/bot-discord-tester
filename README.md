# Discord AI Chatbot Template

so basically this is a simple discord bot that uses AI to chat with your server members. i built this so anyone can just clone it, fill in the env file, and have their own AI chatbot running in like 5 minutes.

it uses Groq API for the AI part which is free and pretty fast, and stores chat history in a local SQLite database so the bot actually remembers what you talked about.

## what it can do

- chat with your members using AI (Llama 3.3, Mixtral, etc)
- remembers each user's conversation separately
- you can change the bot name, personality, basically everything from the .env file without touching the code
- auto detects what language the user is speaking and replies in the same language
- has a cooldown so it doesnt spam or hit rate limits
- wake word system so you can activate it in any channel

## how to set it up

### 1. get the files

```bash
git clone https://github.com/yourusername/discord-ai-bot
cd discord-ai-bot
```

### 2. install the dependencies

```bash
pip install -r requirements.txt
```

### 3. setup your env file

```bash
cp .env.example .env
```

then open `.env` and fill in your values. the only ones you actually need are `DISCORD_TOKEN` and `GROQ_KEY`, the rest are optional.

| variable | required | what it does |
|----------|----------|--------------|
| `DISCORD_TOKEN` | yes | your discord bot token |
| `GROQ_KEY` | yes | your groq api key |
| `BOT_NAME` | no | what you want to call your bot (default: Enki) |
| `BOT_PERSONALITY` | no | the personality/system prompt for the AI |
| `BOT_CREATOR` | no | your name, shows up in the help command |
| `AI_MODEL` | no | which groq model to use |
| `ACTIVE_CHANNEL` | no | channel where bot is always listening (default: ai-chat) |
| `MEMORY_LIMIT` | no | how many messages it remembers per user (default: 15) |
| `COOLDOWN_SECONDS` | no | seconds between responses (default: 3) |

### 4. run it

```bash
python bot.py
```

## getting the API keys

### discord token
1. go to [discord developer portal](https://discord.com/developers/applications)
2. make a new application
3. go to the bot tab and reset the token
4. turn on message content intent and server members intent
5. invite the bot to your server

### groq API key
1. go to [groq console](https://console.groq.com)
2. sign up, its free
3. go to API keys and create one

## how to use it

just talk in the `#ai-chat` channel (or whatever you set as `ACTIVE_CHANNEL`). or you can say `hey <botname>` in any channel to wake it up there.

### commands

| command | what it does |
|---------|--------------|
| `!help` | shows all commands |
| `!ping` | checks latency |
| `!reset` | clears your chat history |
| `!stats` | shows your message count |
| `!uptime` | shows how long the bot has been running |

### wake and sleep
- to wake up: say `hey <botname>` or `<botname> wake up` in any channel
- to put it back to sleep: say `stop <botname>` or `<botname> stop`

## customizing the personality

just edit `BOT_PERSONALITY` in your `.env` file, for example:

```env
BOT_PERSONALITY=You are a sarcastic but helpful assistant. You like making jokes but always give accurate answers.
```

## available AI models

```env
# good balance of speed and quality, recommended
AI_MODEL=llama-3.3-70b-versatile

# fastest option, good for simple stuff
AI_MODEL=llama-3.1-8b-instant

# another good option
AI_MODEL=mixtral-8x7b-32768
```

## deploying it

### railway (free, recommended)
1. push the code to github
2. go to [railway](https://railway.app) and connect your repo
3. add the env variables in the dashboard
4. done

### replit
1. upload the files
2. add secrets for the env variables
3. run it

## file structure

```
discord-ai-bot/
├── bot.py              # main bot file
├── .env.example        # template for your env file
├── .env                # your actual env file (dont push this to github)
├── requirements.txt    # python packages needed
├── chatbot.db          # database, gets created automatically
└── README.md           # this file
```

## license

MIT, do whatever you want with it.
