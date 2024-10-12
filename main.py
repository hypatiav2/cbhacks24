import os
import discord
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
NIM_API_KEY = os.getenv('NIM_API_KEY')

# Intents to monitor messages
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Create a client instance of the bot
client = discord.Client(intents=intents)

# NIM API URL and headers
NIM_API_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
HEADERS = {
    'Authorization': f'Bearer {NIM_API_KEY}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

@client.event
async def on_ready():
    print(f'Bot is ready. Logged in as {client.user}')

@client.event
async def on_message(message):
    # Prevent the bot from responding to itself
    if message.author == client.user:
        return

    # Check if "dm" is in the message to initiate a DM conversation
    if 'dm' in message.content.lower():
        await message.author.send("Let's start a conversation! Send me a message.")

    # Handle DM conversation and use NIM API to generate a response
    if isinstance(message.channel, discord.DMChannel) and message.author != client.user:
        response = get_nim_response(message.content)
        await message.author.send(response)

def get_nim_response(user_input):
    # Prepare the payload similar to the provided curl request
    payload = {
        "messages": [
            {
                "role": "user",
                "content": user_input
            }
        ],
        "stream": False,  # We are not using streaming here
        "model": "meta/llama-3.1-405b-instruct",  # Use the model specified
        "max_tokens": 1024,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "top_p": 0.7,
        "temperature": 0.2
    }

    # Make the POST request to the NVIDIA NIM API
    try:
        response = requests.post(NIM_API_URL, json=payload, headers=HEADERS)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        data = response.json()
        
        # Extract the generated response from the API's result
        generated_text = data.get('choices', [{}])[0].get('message', {}).get('content', "Sorry, I couldn't generate a response.")
        return generated_text
    except requests.exceptions.RequestException as e:
        print(f"Error with NIM API request: {e}")
        return "Oops! Something went wrong while contacting the NVIDIA NIM API."

# Run the bot
client.run(DISCORD_TOKEN)
