import asyncio
import configparser as cp
import json
from functools import partial
from time import mktime, strftime, strptime, time
import sqlite3 as sql

import interactions as i


def setup_database(file: str = "data.db"):
    with sql.connect(file) as conn:
        c = conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS offers (offer_id INTEGER PRIMARY KEY, title TEXT,\
            user_id BIGINT, message_id BIGINT, deadline FLOAT,\
            description TEXT, price TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id))")
        c.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY,\
            offers_count INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS votings (voting_id INTEGER PRIMARY KEY,\
                  user_id BIGINT, message_id BIGINT, deadline FLOAT,\
                  description TEXT, wait_time FLOAT, create_time FLOAT,\
                    FOREIGN KEY(user_id) REFERENCES users(user_id))")
        conn.commit()


setup_database()

with open('config.ini', 'r') as config_file:
    config = cp.ConfigParser()
    config.read_file(config_file)
    TOKEN = config.get('General', 'token')
    SERVER_IDS = config.get('IDs', 'server').split(',')
    privileged_roles_ids = [int(id) for id in config.get(
        'IDs', 'privileged_roles').split(',')]
    offer_channel_id = config.getint('IDs', 'offer_channel')
    voting_channel_id = config.getint('IDs', 'voting_channel')
    voting_role_to_ping_id = config.getint('IDs', 'voting_role_to_ping')


bot = i.Client(
    token=TOKEN, sync_ext=True)

scope_ids = SERVER_IDS
run = False

open("data.json", "a").close()

bot.load_extension("interactions.ext.jurigged")
bot.load_extension("cmds.shop")
bot.load_extension("cmds.wichteln")
bot.load_extension("cmds.offer")
bot.load_extension("cmds.voting")


def json_dump(data_dict: dict) -> None:
    with open("data.json", "w+") as dump_file:
        json.dump(data_dict, dump_file, indent=4)


try:
    with open("data.json", "r+") as data_file:
        data = json.load(data_file)
except json.JSONDecodeError:
    data = {}
    json_dump(data)
votings_timer_started: set = set()


def evaluate_voting(message: i.Message) -> str:
    """Returns the message embed with the voting result appended."""
    winner, winner_count = "", 0
    try:
        winner, winner_count = "", 0
        for reaction in message.reactions:
            if int(reaction.count) > winner_count:
                winner, winner_count = reaction.emoji.name, int(
                    reaction.count)
    except TypeError:
        pass
    message_embed: i.Embed = message.embeds[0]
    message_embed.description = message_embed.description + \
        f"\n\n**Ergebnis:** {winner}"
    return message_embed


async def automatic_delete(oneshot: bool = False) -> None:
    if not oneshot:
        asyncio.get_running_loop().call_later(86400, run_delete)
    offer_channel: i.GuildText = await bot.fetch_channel(offer_channel_id)
    voting_channel: i.GuildText = await bot.fetch_channel(voting_channel_id)
    current_time = time()
    delete_offer_ids, delete_voting_ids = [], []
    with open(data["offer"]["data_file"], "r") as offer_file:
        offer_data: dict = json.load(offer_file)
    for id, values in offer_data["offers"].items():
        if values["deadline"] <= current_time:
            message = await offer_channel.fetch_message(int(values["message_id"]))
            try:
                await message.delete()
            except TypeError:
                continue
            delete_offer_ids.append(id)
            offer_data["count"][values["user_id"]] -= 1

    with open(data["voting"]["data_file"], "r") as voting_file:
        votings_data: dict = json.load(voting_file)
    for id, values in votings_data.items():
        if int(values["deadline"]) <= int(current_time):
            message: i.Message = await voting_channel.fetch_message(int(values["message_id"]))
            message_embed = evaluate_voting(message)
            await message.edit(embeds=message_embed)
            delete_voting_ids.append(id)

    for id in delete_offer_ids:
        del offer_data["offers"][id]
    for id in delete_voting_ids:
        del votings_data[id]

    with open(data["offer"]["data_file"], "w") as offer_file:
        json.dump(offer_data, offer_file, indent=4)
    with open(data["voting"]["data_file"], "w") as voting_file:
        json.dump(votings_data, voting_file, indent=4)


def run_delete(oneshot: bool = False):
    asyncio.get_running_loop().create_task(automatic_delete(oneshot=oneshot))


# Make task that checks the votings file for new votings to start a delete timer
# Go trough all the votings
# Call asyncio.get_running_loop().call_later(wait_time - (localtime - create time), run_delete, oneshot=True)
# Add voting ID to list so there's no duplicate timers
async def check_votings():
    while True:
        with open(data["voting"]["data_file"], "r") as voting_data_file:
            votings: dict = json.load(voting_data_file)
        for id, value_list in votings.items():
            if id not in votings_timer_started:
                asyncio.get_running_loop().call_later(
                    value_list["wait_time"] - (time() - value_list["create_time"]), partial(run_delete, oneshot=True))
                votings_timer_started.add(id)
        await asyncio.sleep(30)


@i.listen()
async def on_ready():
    print("Bot is ready!")
    global run
    if not run:
        wait_time = mktime(strptime(strftime("%d.%m.%Y") +
                           " 23:59", "%d.%m.%Y %H:%M")) - time()
        asyncio.get_running_loop().call_later(wait_time, run_delete)
        asyncio.get_running_loop().create_task(check_votings())
        run = True


@i.slash_command(
    name="test",
    description="A test command to test stuff.",
)
async def test(ctx: i.SlashContext):
    await ctx.send("Test worked!")

bot.start()
