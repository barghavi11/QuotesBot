import discord
import random
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2 import sql

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

def get_db_connection():
    con = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT")
    )
    return con

def setup_database():
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                quoteID SERIAL PRIMARY KEY,
                server_id TEXT,
                channel_id TEXT,
                quote TEXT
            )
        ''')
        con.commit()

setup_database()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!addquote '):
        quote = message.content[10:]
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute('INSERT INTO quotes (server_id, channel_id, quote) VALUES (%s, %s, %s)', 
                        (str(message.guild.id), str(message.channel.id), quote))
            con.commit()
        await message.channel.send(f'Quote: {quote} added!')

    elif message.content.startswith('!quote'):
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute('SELECT quote FROM quotes WHERE server_id=%s', (str(message.guild.id),))
            quotes = cur.fetchall()
        if quotes:
            response = random.choice(quotes)[0]
            await message.channel.send(response)
        else:
            await message.channel.send('No quotes available')

    elif message.content.startswith('!addhistory'):
        channel = message.channel
        await channel.send(f"Adding all quotes from this channel...")

        added_count = 0
        async for msg in channel.history(limit=None):
            if msg.content.startswith('"'):
                with get_db_connection() as con:
                    cur = con.cursor()
                    cur.execute('SELECT 1 FROM quotes WHERE server_id=%s AND channel_id=%s AND quote=%s',
                                (str(message.guild.id), str(channel.id), msg.content))
                    exists = cur.fetchone()
                    if not exists:
                        cur.execute('INSERT INTO quotes (server_id, channel_id, quote) VALUES (%s, %s, %s)', 
                                    (str(message.guild.id), str(channel.id), msg.content))
                        con.commit()
                        added_count += 1
        
        await channel.send(f"Added {added_count} messages to the quote list")

    elif message.content.startswith('!viewquotes'):
        messageList = ""
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute('SELECT quote FROM quotes WHERE server_id=%s', (str(message.guild.id),))
            quotes = cur.fetchall()

        if len(quotes) > 2:
            await message.channel.send(f'There are {len(quotes)} quotes, do you want to view them all?')
            response = await bot.wait_for('message')
            if response.content.lower() == 'yes':
                for quote in quotes:
                    messageList += quote[0] + "\n"
                await message.channel.send("Quotes List: \n\n" + messageList)
            elif response.content.lower() == 'no':
                await message.channel.send('How many quotes would you like to view? Type a number:')
                response = await bot.wait_for('message')
                try:
                    num_to_show = int(response.content)
                    for i in range(num_to_show):
                        messageList += quotes[i][0] + "\n"
                    await message.channel.send(messageList)
                except (ValueError, IndexError):
                    await message.channel.send('Invalid response, returning')
        else:
            for quote in quotes:
                messageList += quote[0] + "\n"
            await message.channel.send("Quote List: \n" + messageList)
            await message.channel.send('End of quotes')

    elif message.content.startswith('!clearquotes'):
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute('DELETE FROM quotes WHERE server_id=%s', (str(message.guild.id),))
            con.commit()
        await message.channel.send('Quotes cleared')

    elif message.content.startswith('!deletequote '):
        quote = message.content[13:]
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute('DELETE FROM quotes WHERE server_id=%s AND quote=%s', 
                        (str(message.guild.id), quote))
            con.commit()
        await message.channel.send(f'Quote: {quote} deleted!')

    elif message.content.startswith('!help'):
        await message.channel.send(
            'Commands: \n\n'
            '!addquote <quote> - adds a quote to the list \n'
            '!quote - gets a random quote \n'
            '!addhistory - adds all messages starting with " in the channel to the quote list \n'
            '!viewquotes - views all quotes in the list \n'
            '!clearquotes - clears all quotes in the list \n'
            '!deletequote <quote> - deletes a quote from the list'
        )

def main():
    bot.run(os.getenv("DISCORD_API_TOKEN"))

if __name__ == "__main__":
    print("Starting bot")
    main()
