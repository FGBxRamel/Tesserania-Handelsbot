import configparser as cp
import json
from random import randint, shuffle
from time import localtime, mktime, sleep, strftime, strptime, time
from os import mkdir, path

import interactions as dc
# TODO Split all the commands into multiple files using extensions... FML

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
emote_chars = ["\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9", "\U0001F1EA",
               "\U0001F1EB", "\U0001F1EC", "\U0001F1ED", "\U0001F1EE", "\U0001F1EF"]

open("data.json", "a").close()

bot.load("cmds.shop")
bot.load("cmds.wichteln")
bot.load("cmds.offer")


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

# ---Abstimmungen---


@bot.command(
    name="abstimmung",
    description="Der Befehl für Abstimmungen.",
    scope=scope_ids,
    options=[
        dc.Option(
            name="aktion",
            description="Das, was du tuen willst.",
            type=dc.OptionType.STRING,
            required=True,
            choices=[
                dc.Choice(
                    name="erstellen",
                    value="create"
                ),
                dc.Choice(
                    name="löschen",
                    value="delete"
                ),
                dc.Choice(
                    name="bearbeiten",
                    value="edit"
                ),
                dc.Choice(
                    name="beenden",
                    value="close"
                )
            ]
        ),
        dc.Option(
            name="id",
            description="Die ID der Abstimmung.",
            type=dc.OptionType.INTEGER,
            required=False
        )
    ]
)
async def votings(ctx: dc.CommandContext, aktion: str, id: int = None):
    if aktion == "create":
        create_voting_modal = dc.Modal(
            title="Abstimmung erstellen",
            custom_id="mod_create_voting",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.PARAGRAPH,
                    label="Welch Volksentscheid wollt ihr verkünden?",
                    custom_id="create_voting_text",
                    required=True,
                    placeholder="Liebe Mitbürger..."
                ),
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="Wie viel Entscheidungen habt ihr zu bieten?",
                    custom_id="create_voting_count",
                    required=True,
                    max_length=2
                ),
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="Wie lange läuft die Abstimmung?",
                    custom_id="create_voting_deadline",
                    required=True,
                    max_length=3
                )
            ]
        )
        await ctx.popup(create_voting_modal)
    elif aktion == "delete":
        delete_modal = dc.Modal(
            title="Abstimmung löschen",
            custom_id="mod_delete_voting",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="ID der Abstimmung",
                    custom_id="delete_voting_id",
                    required=True,
                    min_length=4,
                    max_length=4,
                    value=str(id) if id else ""
                )
            ]
        )
        await ctx.popup(delete_modal)
    elif aktion == "edit":
        edit_voting_modal = dc.Modal(
            title="Abstimmung bearbeiten",
            custom_id="mod_edit_voting",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="ID der Abstimmmung",
                    custom_id="edit_voting_id",
                    required=True,
                    min_length=4,
                    max_length=4,
                    value=str(id) if id else ""
                ),
                dc.TextInput(
                    style=dc.TextStyleType.PARAGRAPH,
                    label="Abstimmungstext",
                    custom_id="edit_voting_text",
                    required=True
                )
            ]
        )
        await ctx.popup(edit_voting_modal)
    elif aktion == "close":
        close_modal = dc.Modal(
            title="Abstimmung beenden",
            custom_id="mod_close_voting",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="ID der Abstimmung",
                    custom_id="close_voting_id",
                    required=True,
                    min_length=4,
                    max_length=4,
                    value=str(id) if id else ""
                )
            ]
        )
        await ctx.popup(close_modal)


@bot.modal("mod_create_voting")
async def create_voting_response(ctx: dc.CommandContext, text: str, count: str, deadline: str):
    if int(count) > 10:
        await ctx.send("""Entschuldige, mehr als 10 Möglichkeiten
            sind aktuell nicht verfügbar.""", ephemeral=True)
        return
    time_type = "Tag(e)"
    if "h" in deadline:
        time_in_seconds = 3600
        deadline = deadline.replace("h", "")
        time_type = "Stunde(n)"
    elif "m" in deadline:
        time_in_seconds = 60
        deadline = deadline.replace("m", "")
        time_type = "Minute(n)"
    else:
        time_in_seconds = 86400
        deadline = deadline.replace("d", "")
    deadline = deadline.replace(",", ".")
    try:
        if float(deadline) < 0:
            deadline = abs(deadline)
        elif float(deadline) == 0:
            await ctx.send("Entschuldige, aber 0 ist keine gültige Zahl.", ephemeral=True)
            return
    except ValueError:
        await ctx.send("Die Uhrzeit hat ein falsches Format.", ephemeral=True)
        return
    identifier = randint(1000, 9999)
    while identifier in data["votings"]:
        identifier = randint(1000, 9999)

    data["votings"][str(identifier)] = {}
    data["votings"][str(identifier)]["user_id"] = str(ctx.author.id)
    data["votings"][str(identifier)]["text"] = text

    count = 2 if int(count) < 2 else count
    end_time = time() + float(deadline) * time_in_seconds
    data["votings"][str(identifier)]["deadline"] = end_time
    wait_time = end_time - time()
    bot._loop.call_later(wait_time, run_delete, True)
    end_time = strftime("%d.%m.") + "- " + \
        strftime("%d.%m. %H:%M", localtime(int(end_time)))

    server: dc.Guild = await ctx.get_guild()
    voting_role_to_ping: dc.Role = await server.get_role(voting_role_to_ping_id)
    voting_embed = dc.Embed(
        title="Liebe Mitbürger",
        description=f"\n{text}",
        color=0xdaa520,
        author=dc.EmbedAuthor(
            name=f"{ctx.user.username}, {end_time} ({deadline} {time_type})"),
        footer=dc.EmbedFooter(text=identifier)
    )
    channel = await ctx.get_channel()
    sent_message = await channel.send(content=voting_role_to_ping.mention, embeds=voting_embed)
    emote_index = 0
    while int(count) > emote_index:
        await sent_message.create_reaction(emote_chars[emote_index])
        emote_index += 1
        sleep(0.5)
    data["votings"][str(identifier)]["message_id"] = str(sent_message.id)
    json_dump(data)
    await ctx.send("Die Abstimmung wurde entgegen genommen.", ephemeral=True)


@bot.modal("mod_delete_voting")
async def delete_voting_response(ctx: dc.CommandContext, id: str):
    try:
        int(id)
    except ValueError:
        await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
        return
    except BaseException as e:
        await ctx.send(
            f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
        return
    if id not in data["votings"]:
        await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
        return
    if not data["votings"][id]["user_id"] == str(ctx.author.id) and not user_is_privileged(ctx.author.roles):
        await ctx.send("Du bist nicht berechtigt diese Abstimmung zu löschen!",
                       ephemeral=True)
        return
    votings_channel: dc.Channel = await ctx.get_channel()
    voting_message: dc.Message = await votings_channel.get_message(data["votings"][id]["message_id"])
    await voting_message.delete(reason=f"[Manuell] {ctx.user.username}")
    del data["votings"][id]
    json_dump(data)
    await ctx.send("Die Abstimmung wurde gelöscht.", ephemeral=True)


@bot.modal("mod_edit_voting")
async def edit_voting_response(ctx: dc.CommandContext, id: str, text: str):
    try:
        int(id)
    except ValueError:
        await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
        return
    except BaseException as e:
        await ctx.send(
            f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
        return
    if id not in data["votings"]:
        await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
        return
    if not data["votings"][id]["user_id"] == str(ctx.author.id):
        await ctx.send("Du bist nicht berechtigt diese Abstimmung zu bearbeiten!",
                       ephemeral=True)
        return
    voting_channel: dc.Channel = await ctx.get_channel()
    voting_message: dc.Message = await voting_channel.get_message(data["votings"][id]["message_id"])
    message_embed: dc.Embed = voting_message.embeds[0]
    text = message_embed.description if type(
        text) is None or text == " " else text
    if "bearbeitet" not in text:
        text = text + "\n*bearbeitet*"
    message_embed.description = text
    server: dc.Guild = await ctx.get_guild()
    voting_role_to_ping: dc.Role = await server.get_role(voting_role_to_ping_id)
    await voting_message.edit(content=voting_role_to_ping.mention, embeds=message_embed)
    await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)


@bot.modal("mod_close_voting")
async def close_voting_response(ctx: dc.CommandContext, id: str):
    try:
        int(id)
    except ValueError:
        await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
        return
    except BaseException as e:
        await ctx.send(
            f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
        return
    if id not in data["votings"]:
        await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
        return
    if not data["votings"][id]["user_id"] == str(ctx.author.id) and not user_is_privileged(ctx.author.roles):
        await ctx.send("Du bist nicht berechtigt diese Abstimmung zu beenden!",
                       ephemeral=True)
        return
    votings_channel: dc.Channel = await ctx.get_channel()
    voting_message: dc.Message = await votings_channel.get_message(data["votings"][id]["message_id"])
    message_embed: dc.Embed = evaluate_voting(voting_message)
    current_time_formatted = strftime("%d.%m. %H:%M")
    message_embed.description = "**Diese Abstimmung wurde vorzeitig beendet!**\n" \
        + f"{ctx.user.username}, {current_time_formatted}" \
        + "\n\n" + message_embed.description
    await voting_message.edit(embeds=message_embed)
    del data["votings"][id]
    json_dump(data)
    await ctx.send("Die Abstimmung wurde beendet.", ephemeral=True)


bot.start()
