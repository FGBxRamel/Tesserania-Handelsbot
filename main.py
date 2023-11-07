import asyncio
import configparser as cp
from functools import partial
from time import mktime, strftime, strptime, time
import database as db

import interactions as i

# TODO Make config section per feature

db.setup()

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

# NOTE Wichtel feature won't be supported anymore; it's there, but without support
bot.load_extension("interactions.ext.jurigged")
bot.load_extension("cmds.shop")
bot.load_extension("cmds.offer")
bot.load_extension("cmds.voting")

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
    offers = db.get_data(
        "offers", attribute="deadline, message_id, offer_id, user_id", fetch_all=True)
    for deadline, message_id, offer_id, user_id in offers:
        if deadline <= current_time:
            message = await offer_channel.fetch_message(message_id)
            try:
                await message.delete()
            except TypeError:
                continue
            db.delete_data("offers", {"offer_id": offer_id})
            offer_count = db.get_data("users", {"user_id": user_id})[1]
            db.update_data("users", "offers_count", offer_count - 1, {
                "user_id": user_id})

    votings = db.get_data(
        "votings", attribute="deadline, message_id, voting_id", fetch_all=True)
    for deadline, message_id, voting_id in votings:
        if deadline <= int(current_time):
            message: i.Message = await voting_channel.fetch_message(message_id)
            message_embed = evaluate_voting(message)
            await message.edit(embeds=message_embed)
            db.delete_data("votings", {"voting_id": voting_id})


def run_delete(oneshot: bool = False):
    asyncio.get_running_loop().create_task(automatic_delete(oneshot=oneshot))


# Make task that checks the votings table for new votings to start a delete timer
# Go trough all the votings
# Call asyncio.get_running_loop().call_later(wait_time - (localtime - create time), run_delete, oneshot=True)
# Add voting ID to list so there's no duplicate timers
# The +2 on the wait time is to mitigate a problem with the computer being too fast
async def check_votings():
    while True:
        votings = db.get_data(
            "votings", attribute="voting_id, wait_time, create_time", fetch_all=True)
        for voting_id, wait_time, create_time in votings:
            if voting_id not in votings_timer_started:
                asyncio.get_running_loop().call_later(
                    wait_time - (time() - create_time) + 2, partial(run_delete, oneshot=True))
                votings_timer_started.add(voting_id)
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
