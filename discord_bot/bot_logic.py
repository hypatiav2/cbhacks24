# discord_bot/bot_logic.py
import discord
from discord import Embed, ButtonStyle, Interaction
from discord.ui import Button, View
import asyncio
from langchain_rag.rag_system import moderate_conversation  # Import the RAG-based moderation logic
import requests
from discord.utils import get

# Discord Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Create a Discord client instance
client = discord.Client(intents=intents)

# Load .env file
import os
from dotenv import load_dotenv
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
KINDO_API_KEY = os.getenv('KINDO_API_KEY')

# Kindo API endpoint and headers
KINDO_API_URL = 'https://llm.kindo.ai/v1/chat/completions'
HEADERS = {
    'api-key': KINDO_API_KEY,
    'content-type': 'application/json'
}

MODERATORS = ["magazine_"]

msg_count = 0

# Function to scan messages for moderation
async def scan_messages(channel):
    try:
        messages = []
        message_objects = []
        async for message in channel.history(limit=10):
            messages.append(f"{message.author.name}: {message.content}")
            message_objects.append(message)
        messages.reverse()
        message_objects.reverse()
        # Use the RAG system to analyze the conversation for moderation purposes
        conversation_text = '\n'.join(messages)
        response = moderate_conversation(conversation_text)
        
        # Extract necessary information from the response
        # Assuming the response returns: 'yes', 'predator_username', 'victim_username'
        result, predator, victim = parse_response(response)

        print(f"result is :{result} predator is {predator} victim is {victim}")
        if result == "yes":
            for message in message_objects:
                if message.author.name == victim:
                    for member in message.guild.members:
                        if member.name == victim:
                            victim = member
                        elif member.name == predator:
                            predator = member

                    print("Sending report...")
                    # Get the link to the first concerning message
                    first_message_link = message.jump_url  # This generates a link to the message
                    await warn_perpetrator_private_thread(channel, predator)
                    # Send an incident report to moderators
                    await send_incident_report(message.guild, victim, predator, first_message_link)
                    
                    print("Engaging victim now...")
                    await engage_victim(message.author, '\n'.join(messages))
                    break
    
    except discord.Forbidden:
        print(f"Cannot access messages in {channel.name}.")
    except discord.HTTPException as e:
        print(f"Failed to retrieve messages from {channel.name}. Error: {e}")

# Helper functions (engage_victim, send_incident_report, etc.) remain similar to what you already have in discord.txt

MODERATORS = ["magazine_"]

# Function to read a file
def read_prompt_file(filename):
    with open(filename, 'r') as file:
        return file.read()


# Function to parse the AI response (extract yes/no, predator, and victim)
def parse_response(response):
    try:
        lines = response.split('\n')
        print("Explanation of below: " + lines[3])
        return lines[0].strip().lower(), lines[1].strip(), lines[2].strip()  # Yes/No, predator, victim
    except IndexError:
        return "no", "", ""  # Default response in case of parsing error

# Function to start a conversation with the victim
async def engage_victim(victim, initial_prompt, model_name="groq/llama3-70b-8192"):
    # Create a new private thread with the victim
    thread = await victim.create_dm()
    if thread:
        counsel_prompt = read_prompt_file('counsel_prompt.txt')
        conversation_history = ""
        while True:
            # Send the current conversation history to the AI
            prompt = f"{counsel_prompt}\n\n Concerning messages in question: {initial_prompt} \n\n Current conversation history:{conversation_history}"
            print("Prompting counsel AI...")
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}]
            }

            try:
                response = requests.post(KINDO_API_URL, headers=HEADERS, json=data)
                response.raise_for_status()
                response_data = response.json()

                ai_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', "No response from the model.")
                conversation_history += f"\nBot: {ai_response}"
                #print(f"Bot: {ai_response}")
                # Send the response to the victim
                await thread.send(ai_response)

                # Wait for the victim's response
                def check(m):
                    return m.channel == thread and m.author == victim

                victim_message = await client.wait_for('message', check=check)

                # Append the victim's response to the conversation history
                conversation_history += f"\nVictim: {victim_message.content}"

                # Check if the victim wants to end the conversation
                if "end" in victim_message.content.lower():
                    await thread.send("Conversation ended. We're always here if you need us.")
                    break

            except requests.exceptions.RequestException as e:
                print(f"Error communicating with Kindo API: {e}")
                break



# Function to send an incident report to moderators with buttons for action
async def send_incident_report(guild, victim, predator, first_message_link):

    # Create a red-colored embed with incident details
    embed = Embed(title="Concerning Behavior Detected",
                  description=f"Victim: {victim.mention}\nPerpetrator: {predator.mention}\n[First Concerning Message]({first_message_link})",
                  color=discord.Color.red())

    embed.add_field(name="Incident Report", value=f"A concerning interaction between {victim.mention} and {predator.mention} was detected.", inline=False)

    # Create buttons: Ignore and Take Action
    ignore_button = Button(label="Ignore", style=ButtonStyle.secondary)
    action_button = Button(label="Take Action", style=ButtonStyle.danger)

    # Define actions for the buttons
    async def ignore_callback(interaction: Interaction):
        await interaction.response.send_message("Incident ignored.", ephemeral=True)

    async def action_callback(interaction: Interaction):
        await interaction.response.send_message(f"Taking action against {predator.mention}. Muting them for 5 minutes...", ephemeral=True)
        # Mute the perpetrator for 5 minutes
        await mute_user(guild, predator, 300)  # 300 seconds = 5 minutes

    ignore_button.callback = ignore_callback
    action_button.callback = action_callback

    # Create a View with the buttons
    view = View()
    view.add_item(ignore_button)
    view.add_item(action_button)
    print(len(guild.members))
    # Send the embed to all moderators
    for member in guild.members:
        print(f"member name: {member.name}")
        if member.name in MODERATORS:
            try:
                await member.send(embed=embed, view=view)
            except discord.Forbidden:
                print(f"Could not DM {member.name}.")


# Function to mute the perpetrator for a specified duration
async def mute_user(guild, user, duration_in_seconds):
    muted_role = discord.utils.get(guild.roles, name="Muted")
    if not muted_role:
        # Create a "Muted" role if it doesn't exist
        muted_role = await guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))

        # Apply the role to all channels
        for channel in guild.channels:
            await channel.set_permissions(muted_role, send_messages=False)

    # Add the "Muted" role to the user
    await user.add_roles(muted_role)

    # Wait for the duration to unmute
    await asyncio.sleep(duration_in_seconds)

    # Remove the "Muted" role from the user
    await user.remove_roles(muted_role)
    await guild.system_channel.send(f"{user.mention} has been unmuted.")

async def warn_perpetrator_private_thread(channel, perpetrator):
    # Create a private thread in the relevant channel
    thread = await channel.create_thread(
        name=f"Private Warning for {perpetrator.name}",
        type=discord.ChannelType.private_thread,
        invitable=False  # Other users can't be invited
    )

    # Add the perpetrator to the thread
    await thread.add_user(perpetrator)

    # Send a message in the thread visible only to the bot and the perpetrator
    await thread.send(f"Be mindful of what you say — our moderation tools have detected unusual content in this channel.")


# Event handler when the bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    # Continuously scan each text channel in every server the bot is in
    for guild in client.guilds:
            channel = get(guild.text_channels, name="test4")
            await scan_messages(channel)

# Event handler when a message is sent in the server
@client.event
async def on_message(message):
    global msg_count
    msg_count += 1
    # Avoid the bot responding to itself
    if message.author == client.user:
        return

    # If the message contains "bot", scan the last 10 messages for moderation
    if 'bot' in message.content.lower() or msg_count == 25:
        print("Scanning now..")
        msg_count = 0
        await scan_messages(message.channel)
