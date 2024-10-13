# main.py
from discord_bot.bot_logic import client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

if __name__ == "__main__":
    # Start the bot
    client.run(DISCORD_TOKEN)
