import os
import discord
from dotenv import load_dotenv

# Load the .env file containing the bot token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Intents are needed for monitoring messages in all channels
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Create a client instance of the bot
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot is ready. Logged in as {client.user}')

@client.event
async def on_message(message):
    # Don't let the bot reply to itself
    if message.author == client.user:
        return

    # Check if the message contains the word "bot"
    if 'bot' in message.content.lower():
        await message.channel.send(f'You mentioned "bot", {message.author.mention}!')
    
    # Check if the message contains the word "dm"
    if 'dm' in message.content.lower():
        # Send a DM to the user
        try:
            await message.author.send("Here's a direct message just for you!")
        except discord.Forbidden:
            await message.channel.send(f"Sorry {message.author.mention}, I can't send you a DM.")
   
# Run the bot with the token
client.run(TOKEN)
