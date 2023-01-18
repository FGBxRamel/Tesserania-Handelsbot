import configparser as cp
import json
from random import randint, shuffle
from time import localtime, mktime, sleep, strftime, strptime, time
from os import mkdir, path

import interactions as dc

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


bot = dc.Client(
    token=TOKEN)

scope_ids = SERVER_IDS
run = False

open("data.json", "a").close()

bot.load("cmds.shop")
bot.load("cmds.wichteln")
bot.load("cmds.offer")
bot.load("cmds.voting")


def json_dump(data_dict: dict) -> None:
    with open("data.json", "w+") as dump_file:
        json.dump(data_dict, dump_file, indent=4)


def user_is_privileged(roles: list) -> bool:
    return any(role in privileged_roles_ids for role in roles)


try:
    with open("data.json", "r+") as data_file:
        data = json.load(data_file)
except json.JSONDecodeError:
    data = {}
sections = ["votings"]
for section in sections:
    if section not in data:
        data[section] = {}

json_dump(data)


def evaluate_voting(message: dc.Message) -> str:
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
    message_embed: dc.Embed = message.embeds[0]
    message_embed.description = message_embed.description + \
        f"\n\n**Ergebnis:** {winner}"
    return message_embed


async def automatic_delete(oneshot: bool = False) -> None:
    if not oneshot:
        bot._loop.call_later(86400, run_delete)
    offer_channel: dc.Channel = await dc.get(bot, dc.Channel, channel_id=offer_channel_id)
    voting_channel: dc.Channel = await dc.get(bot, dc.Channel, channel_id=voting_channel_id)
    current_time = time()
    delete_offer_ids, delete_voting_ids = [], []
    with open(data["offer"]["data_file"], "r") as offer_file:
        offer_data: dict = json.load(offer_file)
    for id, values in offer_data["offers"].items():
        if values["deadline"] <= current_time:
            message = await offer_channel.get_message(int(values["message_id"]))
            try:
                await message.delete("[Auto] Cleanup")
            except TypeError:
                continue
            delete_offer_ids.append(id)
            offer_data["count"][values["user_id"]] -= 1

    for id, values in data["votings"].items():
        if values["deadline"] <= current_time:
            message: dc.Message = await voting_channel.get_message(int(values["message_id"]))
            message_embed = evaluate_voting(message)
            await message.edit(embeds=message_embed)
            delete_voting_ids.append(id)

    for id in delete_offer_ids:
        del offer_data["offers"][id]
    for id in delete_voting_ids:
        del data["votings"][id]

    with open(data["offer"]["data_file"], "w+") as offer_file:
        json.dump(offer_data, offer_file, indent=4)
    json_dump(data)


def run_delete(oneshot: bool = False):
    bot._loop.create_task(automatic_delete(oneshot=oneshot))


# Make task that checks the data file for new votings to start a delete timer
# Go trough all the votings (structure:
# {votings: [{"id": [create_time, wait_time]}]}
# )
# Call bot._loop.call_later(wait_time - (localtime - create time), run_delete, oneshot=True)
async def check_votings():
    with open("data.json", "r+") as data_file:
        data = json.load(data_file)
    for id, value_list in data["votings"].items():
        bot._loop.call_later(
            value_list[1] - (time() - value_list[0]), run_delete, oneshot=True)
        del data["votings"][id]
    json_dump(data)

bot._loop.create_task(check_votings())


@bot.event()
async def on_ready():
    global run
    if not run:
        wait_time = mktime(strptime(strftime("%d.%m.%Y") +
                           " 23:59", "%d.%m.%Y %H:%M")) - time()
        bot._loop.call_later(wait_time, run_delete)
        run = True


@bot.command(
    name="test",
    description="A test command to test stuff.",
)
async def test(ctx: dc.CommandContext):
    await ctx.send("Test worked!")

bot.start()
