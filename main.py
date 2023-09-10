import aiosqlite
from discord.ext import commands, tasks
from keep_alive import keep_alive
import os, json, re, asyncio, random
import numpy as np
from PIL import Image
from io import BytesIO
from tensorflow.keras.models import load_model
import aiohttp
import discord
import string

TOKEN = os.environ["token"]
guild = os.environ["server"]
ownerid = int(os.environ["ownerid"])
spamid = int(os.environ["spamid"])
captchachannel = int(os.environ["captcha"])

timerlist = [1.0, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
intervals = [2.5, 3, 3.5, 4, 4.5, 5]

is_spamming = False

bot_prefix = "."
bot = commands.Bot(command_prefix=".")
loaded_model = load_model('model.h5', compile=False)
with open('classes.json', 'r') as f:
    classes = json.load(f)

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()


def solve(message):
    hint = []
    for i in range(15, len(message) - 1):
        if message[i] != '\\':
            hint.append(message[i])
    hint_string = ''
    for i in hint:
        hint_string += i
    hint_replaced = hint_string.replace('_', '.')
    return re.findall('^' + hint_replaced + '$', pokemon_list, re.MULTILINE)


@tasks.loop(seconds=random.choice(intervals))
async def spam():
    if is_spamming:
        channel = bot.get_channel(spamid)
        message = "".join(
            random.choices(string.ascii_uppercase + string.ascii_lowercase +
                           string.digits,
                           k=random.randint(12, 24)))
        nmessage = message + " | PokeNemesis Spamming Services Is On"
        await channel.send(nmessage)


async def catch(message: discord.Message):
    c = await bot.loop.run_in_executor(None, solve, message.content)
    ch = message.channel
    if not len(c):
        await ch.send("Couldn't Find The Pokemon")
    else:
        for i in c:
            await ch.send(f'<@716390085896962058> c {i}')


@spam.before_loop
async def before_spam():
    await bot.wait_until_ready()


@spam.after_loop
async def after_spam():
    if not bot.is_closed():
        await spam.stop()


@bot.event
async def on_ready():

    global is_spamming
  
    await bot.change_presence(status=discord.Status.online)
    print('------- Logged In As : {0.user}'.format(bot))
    bot.db = await aiosqlite.connect("pokemon.db")
    await bot.db.execute("CREATE TABLE IF NOT EXISTS pokies (command str)")
    print("------- Pokies Table Created -------")
    await bot.db.commit()

    is_spamming = True
    spam.start()


@bot.event
async def on_message(message):

    global is_spamming

    while not hasattr(bot, 'db'):
        await asyncio.sleep(1.0)
    if message.guild.id == int(guild):
        if message.author.id == 716390085896962058:
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                if "appeared!" in embed.title:

                    is_spamming = False
                    cur = await bot.db.execute("SELECT command from pokies")
                    res = await cur.fetchone()
                    if res is None or res[0] != "hold":
                        if embed.image:
                            url = embed.image.url
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url=url) as resp:
                                    if resp.status == 200:
                                        content = await resp.read()
                                        image_data = BytesIO(content)
                                        image = Image.open(image_data)
                            preprocessed_image = await preprocess_image(image)
                            predictions = loaded_model.predict(
                                preprocessed_image)
                            classes_x = np.argmax(predictions, axis=1)
                            name = list(classes.keys())[classes_x[0]]
                            is_spamming = True
                            async with message.channel.typing():

                                await asyncio.sleep(random.choice(timerlist))

                                await message.channel.send(
                                    f'<@716390085896962058> c {name}')

                elif "Pride Buddy" in embed.title:
                    await asyncio.sleep(3)
                    await message.components[0].children[0].click()
            elif 'wrong' in message.content:
                await asyncio.sleep(1)
                await message.channel.send('<@716390085896962058> h')
            elif 'The pokémon is' in message.content:
                await asyncio.sleep(1)
                await catch(message)
            elif 'This will override' in message.content:
                await asyncio.sleep(2)
                await message.components[0].children[0].click()

            elif 'human' in message.content:
                is_spamming = False
                cur = await bot.db.execute("SELECT command from pokies")
                res = await cur.fetchone()
                if res is None:
                    await bot.db.execute(
                        "INSERT OR IGNORE INTO pokies (command) VALUES (?)",
                        ("hold", ))
                else:
                    await bot.db.execute("UPDATE pokies SET command = ?",
                                         ("hold", ))
                await bot.db.commit()
                pattern = r'https://verify\.poketwo\.net/captcha/[0-9]+'
                match = re.search(pattern, message.content)
                if match:
                    url = match.group()
                    cnl = bot.get_channel(captchachannel)
                    await asyncio.sleep(1)
                    await cnl.send("Captcha Came Solve It")
                    is_spamming = False
                    await message.author.kick()
                    channel = bot.get_channel(captchachannel)
                    await asyncio.sleep(2)
                    await channel.send(
                        f"<@{ownerid}> Please Verify The Captcha {url}\nAfter Verification Use : `{bot_prefix}captcha done`"
                    )
        elif message.author.id == ownerid:
            if f"{bot_prefix}say" in message.content:
                msg = message.content.split(" ", 1)[1]
                await message.delete()
                await message.channel.send(msg)
            elif f"{bot_prefix}start" in message.content or "captcha done" in message.content:

                if f"{bot_prefix}start" in message.content:
                    async with message.channel.typing():
                        await asyncio.sleep(2.0)
                    await message.channel.send("Ok Let's Go")
                    is_spamming = True
                else:
                    async with message.channel.typing():
                        await asyncio.sleep(2.0)
                    await message.channel.send("Thanks | Now Let's Grind")
                    is_spamming = True
                cur = await bot.db.execute("SELECT command from pokies")
                res = await cur.fetchone()
                if res is None:
                    await bot.db.execute(
                        "INSERT OR IGNORE INTO pokies (command) VALUES (?)",
                        ("grind", ))
                else:
                    await bot.db.execute("UPDATE pokies SET command = ?",
                                         ("grind", ))
                await bot.db.commit()
            elif f"{bot_prefix}stop" in message.content:
                await message.delete()
                async with message.channel.typing():
                    await asyncio.sleep(2.0)
                is_spamming = False
                await message.channel.send("Ok I Am Going To Sleep")
                cur = await bot.db.execute("SELECT command from pokies")
                res = await cur.fetchone()
                if res is None:
                    await bot.db.execute(
                        "INSERT OR IGNORE INTO pokies (command) VALUES (?)",
                        ("hold", ))
                else:
                    await bot.db.execute("UPDATE pokies SET command = ?",
                                         ("hold", ))
                await bot.db.commit()

    elif message.channel in bot.private_channels:
        if message.author.id == ownerid:
            if f"{bot_prefix}say" in message.content:
                msg = message.content.split(" ", 2)
                catch_id = msg[1]
                if catch_id.isdigit():
                    catchchannel = bot.get_channel(catch_id)
                else:
                    async with message.channel.typing():
                        await asyncio.sleep(3.0)
                    await message.channel.send(
                        "When You Use A Command In The DM, Please Meantion The Channel ID | Example: ```.say 973828282874 Hello Friends```"
                    )
                    return
                if catch_id:
                    async with message.channel.typing():
                        await asyncio.sleep(2.0)
                    await catchchannel.send(msg[2])
                else:
                    async with message.channel.typing():
                        await asyncio.sleep(3.0)
                    await message.channel.send(
                        "Incorrect Channel Id | Make Sure I Am Present In The Server With Access"
                    )

            elif f"{bot_prefix}start" in message.content or "captcha done" in message.content:
                if f"{bot_prefix}start" in message.content:
                    await message.channel.send("Ok Let's Go")
                else:
                    await message.channel.send("Thanks | Now Let's Grind")
                cur = await bot.db.execute("SELECT command from pokies")
                res = await cur.fetchone()
                if res is None:
                    await bot.db.execute(
                        "INSERT OR IGNORE INTO pokies (command) VALUES (?)",
                        ("grind", ))
                else:
                    await bot.db.execute("UPDATE pokies SET command = ?",
                                         ("grind", ))
                await bot.db.commit()
            elif f"{bot_prefix}stop" in message.content:
                await message.channel.send("Ok I Am Going To Sleep")
                cur = await bot.db.execute("SELECT command from pokies")
                res = await cur.fetchone()
                if res is None:
                    await bot.db.execute(
                        "INSERT OR IGNORE INTO pokies (command) VALUES (?)",
                        ("hold", ))
                else:
                    await bot.db.execute("UPDATE pokies SET command = ?",
                                         ("hold", ))
                await bot.db.commit()
            else:
                await bot.process_commands(message)


async def preprocess_image(image):
    image = image.resize((64, 64))
    image = np.array(image)
    image = image / 255.0
    image = np.expand_dims(image, axis=0)
    return image


@bot.command()
async def start_spam(ctx):
    global is_spamming
    is_spamming = True
    spam.start()
    await ctx.send("Spamming started.")


@bot.command()
async def stop_spam(ctx):
    global is_spamming
    is_spamming = False
    spam.stop()
    await ctx.send("Spamming stopped.")


keep_alive()
bot.run(TOKEN, log_handler=None)
