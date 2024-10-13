import os
import discord
import requests
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory

# Load the .env file to get the Discord token and Kindo API key
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
KINDO_API_KEY = os.getenv('KINDO_API_KEY')

# Discord Intents (required for reading messages)
intents = discord.Intents.default()
intents.message_content = True

# Create a Discord client instance
client = discord.Client(intents=intents)

# Kindo API endpoint and headers
KINDO_API_URL = 'https://llm.kindo.ai/v1/chat/completions'
HEADERS = {
    'api-key': KINDO_API_KEY,
    'content-type': 'application/json'
}

# Memory object to store conversation history
memory = ConversationBufferMemory()

# Function to send a message to the Kindo API and get a response
def get_kindo_llm_response(conversation_history, model_name="groq/llama3-70b-8192"):
    data = {
        "model": model_name,
        "messages": conversation_history  # Send the whole conversation history
    }

    try:
        response = requests.post(KINDO_API_URL, headers=HEADERS, json=data)
        response.raise_for_status()  # Check for errors in the response
        response_data = response.json()

        # Extract the generated response
        return response_data.get('choices', [{}])[0].get('message', {}).get('content', "No response from the model.")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Kindo API: {e}")
        return "Sorry, something went wrong with the Kindo API."

# When the bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

# Event handler for when a message is sent in the server
@client.event
async def on_message(message):
    # Avoid the bot responding to itself
    if message.author == client.user:
        return

    # Check if the message is in a server (not a DM) and contains the word 'bot'
    if message.guild and 'bot' in message.content.lower():
        await message.channel.send("You mentioned me! I'll respond soon.")

        # Get the conversation history from Langchain memory
        conversation_history = memory.load_memory_variables({})['history']
        
        # Prepare the conversation history in the format the API expects
        conversation_messages = [
            {"role": "user", "content": msg}
            for msg in conversation_history.split("\n")
        ]

        # Get the response from the Kindo API
        response = get_kindo_llm_response(conversation_messages)

        # Save user message and bot response in memory
        memory.save_context({"role": "user", "content": message.content}, {"role": "assistant", "content": response})

        # Send the response back to the same channel
        await message.channel.send(response)

    # Handle direct message (DM) conversation
    if isinstance(message.channel, discord.DMChannel):
        # Get the conversation history from Langchain memory
        conversation_history = memory.load_memory_variables({})['history']
        
        # Prepare the conversation history in the format the API expects
        conversation_messages = [
            {"role": "user", "content": msg}
            for msg in conversation_history.split("\n")
        ]

        # Get the response from the Kindo API
        response = get_kindo_llm_response(conversation_messages)

        # Save user message and bot response in memory
        memory.save_context({"role": "user", "content": message.content}, {"role": "assistant", "content": response})

        # Send the response back via DM
        await message.author.send(response)

# Run the bot
client.run(DISCORD_TOKEN)
