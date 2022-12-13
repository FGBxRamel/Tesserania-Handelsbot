import configparser as cp
import json
import re
from random import randint, shuffle
from time import localtime, mktime, sleep, strftime, strptime, time
from copy import deepcopy

import interactions as dc
from interactions.ext.get import get

with open('config.ini', 'r') as config_file:
    config = cp.ConfigParser()
    config.read_file(config_file)

    TOKEN = config.get('General', 'token')
    server_ids = config.get('IDs', 'server').split(',')
    privileged_roles_ids = [int(id) for id in config.get(
        'IDs', 'privileged_roles').split(',')]
    voting_role_to_ping_id = int(config.get('IDs', 'voting_role_to_ping'))
    minecrafter_role_id = int(config.get('IDs', 'minecrafter_role'))
    offer_channel_id = int(config.get('IDs', 'offer_channel'))
    voting_channel_id = int(config.get('IDs', 'voting_channel'))

    shop_count_limit = int(config.get('Shops', 'max_shops_per_person'))
    shop_categories = config.get('Shops', 'categories').split(',')
    shop_categories_excluded_from_limit = config.get(
        'Shops', 'categories_excluded_from_limit').split(",")

bot = dc.Client(
    token=TOKEN)

scope_ids = server_ids
run = False
emote_chars = ["\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9", "\U0001F1EA",
               "\U0001F1EB", "\U0001F1EC", "\U0001F1ED", "\U0001F1EE", "\U0001F1EF"]

open("data.json", "a").close()
open("wichteln.txt", "a").close()


def implement(json_object: dict) -> dict:
    data_dict = {}
    for key, value in json_object.items():
        if type(value) is dict and key in data_dict:
            data_dict[key] = implement(value)
        else:
            data_dict[key] = value
    return data_dict


def json_dump(data_dict: dict) -> None:
    with open("data.json", "w+") as dump_file:
        json.dump(data_dict, dump_file, indent=4)


def user_is_privileged(roles: list) -> bool:
    return any(role in privileged_roles_ids for role in roles)


try:
    with open("data.json", "r+") as data_file:
        data = implement(json.load(data_file))
except json.JSONDecodeError:
    data = {}
sections = ["offers", "count", "votings", "wichteln", "shop"]
for section in sections:
    if section not in data:
        data[section] = {}
subsections = {"wichteln": {"active": False,
                            "participants": []}, "shop": {"count": {}, "shops": {}}}
for section, subsections in subsections.items():
    for subsection, value in subsections.items():
        if subsection not in data[section]:
            data[section][subsection] = value

json_dump(data)

shop_transfer_data = {}


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
    offer_channel = await get(bot, dc.Channel, channel_id=offer_channel_id)
    voting_channel = await get(bot, dc.Channel, channel_id=voting_channel_id)
    current_time = time()
    delete_offer_ids, delete_voting_ids = [], []
    for id, values in data["offers"].items():
        if values["deadline"] <= current_time:
            message = await offer_channel.get_message(int(values["message_id"]))
            try:
                await message.delete("[Auto] Cleanup")
            except TypeError:
                continue
            delete_offer_ids.append(id)
            data["count"][values["user_id"]
                          ] = data["count"][values["user_id"]] - 1

    for id, values in data["votings"].items():
        if values["deadline"] <= current_time:
            message: dc.Message = await voting_channel.get_message(int(values["message_id"]))
            message_embed = evaluate_voting(message)
            await message.edit(embeds=message_embed)
            delete_voting_ids.append(id)

    for id in delete_offer_ids:
        del data["offers"][id]
    for id in delete_voting_ids:
        del data["votings"][id]
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
    scope=scope_ids
)
async def test(ctx: dc.CommandContext):
    await ctx.send("Test worked!")

# ---Offer---


@bot.command(
    name="angebot",
    description="Der Befehl für Angebote.",
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
                )
            ]
        ),
        dc.Option(
            name="id",
            description="Die ID des Angebots.",
            type=dc.OptionType.INTEGER,
            required=False
        )
    ]
)
async def offer(ctx: dc.CommandContext, aktion: str, id: int = None):
    if aktion == "create":
        if not str(ctx.author.id) in data["count"]:
            data["count"][str(ctx.author.id)] = 0
        elif data["count"][str(ctx.author.id)] >= 3:
            await ctx.send("Zum Erwerb dargeboten werden dürfen nur drei Waren.", ephemeral=True)
            return
        create_modal = dc.Modal(
            title="Angebot erstellen",
            custom_id="mod_create_offer",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="Titel",
                    custom_id="create_offer_title",
                    required=True
                ),
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="Preis",
                    custom_id="create_offer_price",
                    value="VB"
                ),
                dc.TextInput(
                    style=dc.TextStyleType.PARAGRAPH,
                    label="Was bietest du an?",
                    custom_id="create_offer_text",
                    required=True
                ),
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="Wie lange läuft das Angebot? (1-7)",
                    custom_id="create_offer_deadline",
                    required=True,
                    max_length=1
                )
            ]
        )
        await ctx.popup(create_modal)
    elif aktion == "delete":
        delete_modal = dc.Modal(
            title="Angebot löschen",
            custom_id="mod_delete_offer",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="ID des Angebots",
                    custom_id="delete_offer_id",
                    required=True,
                    min_length=4,
                    max_length=4,
                    value=str(id) if id else ""
                )
            ]
        )
        await ctx.popup(delete_modal)
    elif aktion == "edit":
        edit_id_modal = dc.Modal(
            title="Angebot bearbeiten",
            ustom_id="mod_edit_offer",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="Titel",
                    custom_id="edit_offer_title",
                    value=data["offers"][str(id)]["title"] if id else ""
                ),
                dc.TextInput(
                    style=dc.TextStyleType.PARAGRAPH,
                    label="Angebotstext",
                    custom_id="edit_offer_text",
                    value=data["offers"][str(id)]["text"] if id else ""
                ),
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="ID des Angebots",
                    custom_id="edit_offer_id",
                    required=True,
                    min_length=4,
                    max_length=4
                )
            ]
        )
        await ctx.popup(edit_id_modal)


@bot.modal("mod_create_offer")
async def create_offer_respone(ctx: dc.CommandContext, title: str, price: str, offer_text: str, deadline: str):
    identifier = randint(1000, 9999)
    while identifier in data["offers"]:
        identifier = randint(1000, 9999)
    data["offers"][str(identifier)] = {}
    data["offers"][str(identifier)]["user_id"] = str(ctx.author.id)
    data["offers"][str(identifier)]["price"] = str(price)
    data["offers"][str(identifier)]["text"] = str(offer_text)
    if int(deadline) < 1:
        deadline = 1
    elif int(deadline) > 7:
        deadline = 7
    # The deadline is: current_time_seconds_epoch + x * seconds_of_one_day
    end_time = time() + int(deadline) * 86400
    data["offers"][str(identifier)]["deadline"] = end_time
    end_time = strftime("%d.%m.") + "- " + \
        strftime("%d.%m.", localtime(end_time))
    app_embed = dc.Embed(
        title=title,
        description=f"\n{offer_text}\n\n**Preis:** {price}",
        color=0xdaa520,
        author=dc.EmbedAuthor(
            name=f"{ctx.user.username}, {end_time} ({deadline} Tage)"),
        footer=dc.EmbedFooter(text=identifier)
    )
    channel = await ctx.get_channel()
    sent_message = await channel.send(embeds=app_embed)
    data["offers"][str(identifier)]["message_id"] = str(sent_message.id)
    data["count"][str(ctx.author.id)] = data["count"][str(ctx.author.id)] + 1
    json_dump(data)
    await ctx.send("Das Angebot wurde entgegen genommen.", ephemeral=True)


@bot.modal("mod_delete_offer")
async def delete_offer_response(ctx: dc.CommandContext, id: str):
    try:
        int(id)
    except ValueError:
        await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
        return
    except BaseException as e:
        await ctx.send(
            f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
        return
    if id not in data["offers"]:
        await ctx.send("Diese ID existiert nicht!", ephemeral=True)
        return
    if not data["offers"][id]["user_id"] == str(ctx.author.id) and not user_is_privileged(ctx.author.roles):
        await ctx.send("Du bist nicht berechtigt dieses Angebot zu löschen!",
                       ephemeral=True)
        return
    offer_channel: dc.Channel = await ctx.get_channel()
    offer_message: dc.Message = await offer_channel.get_message(data["offers"][id]["message_id"])
    await offer_message.delete(reason=f"[Manuell] {ctx.author.user.username}")
    del data["offers"][id]
    data["count"][str(ctx.author.id)] = data["count"][str(ctx.author.id)] - 1
    json_dump(data)
    await ctx.send("Das Angebot wurde gelöscht.", ephemeral=True)


@bot.modal("mod_edit_offer")
async def edit_offer_id(ctx: dc.CommandContext, title: str, text: str, id: str = ""):
    try:
        int(id)
    except ValueError:
        await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
        return
    except BaseException as e:
        await ctx.send(
            f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
        return
    if id not in data["offers"]:
        await ctx.send("Diese ID existiert nicht!", ephemeral=True)
        return
    if not data["offers"][id]["user_id"] == str(ctx.author.id):
        await ctx.send("Du bist nicht berechtigt dieses Angebot zu bearbeiten!",
                       ephemeral=True)
        return
    offer_channel: dc.Channel = await ctx.get_channel()
    offer_message: dc.Message = await offer_channel.get_message(data["offers"][id]["message_id"])
    message_embed: dc.Embed = offer_message.embeds[0]
    if type(title) is None or title == " ":
        title = message_embed.title
    if type(text) is None or text == " ":
        text = message_embed.description + "\n*bearbeitet*"
    else:
        text = f"{text}\n**Preis:** {data['offers'][id]['price']}\n*bearbeitet*"
    message_embed.title = title
    message_embed.description = text
    await offer_message.edit(embeds=message_embed)
    await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)

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


@bot.command(
    name="wichteln",
    description="Der Befehl für das Wichteln.",
    scope=scope_ids,
    options=[
        dc.Option(
            name="aktion",
            description="Das, was du tuen willst.",
            type=dc.OptionType.STRING,
            required=True,
            choices=[
                dc.Choice(
                    name="starten",
                    value="start"
                ),
                dc.Choice(
                    name="beenden",
                    value="end"
                ),
                dc.Choice(
                    name="bearbeiten",
                    value="edit"
                )
            ]
        ),
        dc.Option(
            name="kanal",
            description="Der Kanal, in dem die Wichtelung stattfinden soll.",
            type=dc.OptionType.CHANNEL,
            required=False
        ),
    ]
)
async def wichteln(ctx: dc.CommandContext, aktion: str, kanal: dc.Channel = None):
    if aktion == "start":
        if not kanal:
            await ctx.send("Du musst einen Kanal angeben!", ephemeral=True)
            return
        if data["wichteln"]["active"]:
            await ctx.send("Es gibt bereits eine Wichtelung.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        data["wichteln"]["participants"] = []
        text = ""
        with open("wichteln.txt", "r") as f:
            text = f.read()
        text.replace("$year$", strftime("%Y"))
        wichteln_embed = dc.Embed(
            title="Wichteln",
            description=text
        )
        guild: dc.Guild = await ctx.get_guild()
        minecrafter_role: dc.Role = await guild.get_role(minecrafter_role_id)
        await kanal.send(content=minecrafter_role.mention, embeds=wichteln_embed)
        participants: list[dc.Member] = []
        guild_members = await guild.get_all_members()
        for member in guild_members:
            if minecrafter_role_id in member.roles:
                participants.append(member)
        shuffle(participants)
        participants.append(participants[0])
        i = 0
        for participant in participants:
            if i == len(participants) - 1:
                break
            data["wichteln"]["participants"].append(int(participant.id))
            partner = participants[i + 1].user.username
            await participant.send(f"Du bist Wichtel von {partner}!\nFür mehr Infos schaue bitte auf {guild.name}.")
            i += 1
        data["wichteln"]["active"] = True
        json_dump(data)
        await ctx.send("Die Wichtelung wurde erstellt.", ephemeral=True)
    elif aktion == "end":
        if not data["wichteln"]["active"]:
            await ctx.send("Es gibt keine aktive Wichtelung.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        guild: dc.Guild = await ctx.get_guild()
        guild_id = int(guild.id)
        participants = await dc.get(bot, list[dc.Member], parent_id=guild_id, object_ids=data["wichteln"]["participants"])
        for participant in participants:
            await participant.send(f"Die Wichtelung von {guild.name} wurde beendet.")
        data["wichteln"]["active"] = False
        json_dump(data)
        await ctx.send("Die Wichtelung wurde beendet.", ephemeral=True)
    elif aktion == "edit":
        with open("wichteln.txt", "r") as f:
            text = f.read()
        wichteln_text_modal = dc.Modal(
            title="Wichteltext bearbeiten",
            description="Hier kannst du den Text für die Wichtelung bearbeiten.",
            custom_id="wichteln_text",
            components=[
                dc.TextInput(
                    label="Text",
                    placeholder="Text",
                    value=text,
                    custom_id="text",
                    style=dc.TextStyleType.PARAGRAPH,
                    required=True
                )
            ]
        )
        await ctx.popup(wichteln_text_modal)


@bot.modal("wichteln_text")
async def wichteln_text_response(ctx: dc.CommandContext, text: str):
    with open("wichteln.txt", "w") as f:
        f.write(text)
    text = text.replace("$year$", strftime("%Y"))
    wichteln_text_preview_embed = dc.Embed(
        title="Textvorschau",
        description=text
    )
    await ctx.send("Der Text wurde gespeichert.", ephemeral=True, embeds=wichteln_text_preview_embed)


categories = []
for category in shop_categories:
    option = dc.SelectOption(
        label=category,
        value=category
    )
    categories.append(option)

categorie_selectmenu = dc.SelectMenu(
    custom_id="categorie_select",
    placeholder="Kategorie",
    options=categories
)
shop_abort_button = dc.Button(
    label="Abbrechen",
    custom_id="shop_abort",
    style=dc.ButtonStyle.DANGER
)


def get_shop_ids_select_options() -> list[dc.SelectOption]:
    options = []
    for shop_id, shop_data in data["shop"]["shops"].items():
        option = dc.SelectOption(
            label=shop_id,
            value=str(shop_id),
            description=shop_data["name"]
        )
        options.append(option)
    return options


@bot.command(
    name="shop",
    description="Der Command für das Handelsregister.",
    scope=scope_ids,
    options=[
        dc.Option(
            name="aktion",
            description="Die Aktion, die du ausführen möchtest.",
            type=dc.OptionType.STRING,
            required=True,
            choices=[
                dc.Choice(
                    name="eintragen",
                    value="create"
                ),
                dc.Choice(
                    name="bearbeiten",
                    value="edit"
                ),
                dc.Choice(
                    name="löschen",
                    value="delete"
                )
            ]
        ),
        dc.Option(
            name="id",
            description="Die ID des Shops, den du bearbeiten oder löschen möchtest.",
            type=dc.OptionType.INTEGER,
            required=False,
            min_value=1000,
            max_value=9999
        )
    ]
)
async def shop(ctx: dc.CommandContext, aktion: str, id: str = None):
    if id:
        try:
            int(id)
            id = str(id)
        except ValueError:
            await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
            return
    if aktion == "create":
        identifier = str(randint(1000, 9999))
        while identifier in data["shop"]["shops"] or identifier in shop_transfer_data:
            identifier = str(randint(1000, 9999))
        shop_transfer_data[identifier] = {}
        row1 = dc.ActionRow(components=[categorie_selectmenu])
        row2 = dc.ActionRow(components=[shop_abort_button])
        sent_message = await ctx.send(f"""|| {identifier} ||
        Bitte wähle eine Kategorie:""", components=[row1, row2], ephemeral=True)
        shop_transfer_data[identifier]["message_id"] = sent_message.id
    elif aktion == "edit":
        await ctx.send("Dieser Command ist noch nicht verfügbar.", ephemeral=True)
    elif aktion == "delete":
        if id:
            if id in data["shop"]["shops"]:
                if not ctx.author.id == data["shop"]["shops"][id]["owner"] or not user_is_privileged(ctx.author.roles):
                    await ctx.send("Du bist nicht der Besitzer dieses Shops!", ephemeral=True)
                    return
                shop_message = await ctx.channel.get_message(data["shop"]["shops"][id]["message_id"])
                await shop_message.delete()
                if not data["shop"]["shops"][id]["categorie"] in shop_categories_excluded_from_limit:
                    data["shop"]["count"][str(ctx.author.id)] -= 1
                del data["shop"]["shops"][id]
                json_dump(data)
                await ctx.send("Der Shop wurde gelöscht.", ephemeral=True)
            else:
                await ctx.send("Der Shop existiert nicht!", ephemeral=True)
        else:
            shop_ids_select_options = get_shop_ids_select_options()
            shop_ids_selectmenu = dc.SelectMenu(
                custom_id="shop_id_select",
                placeholder="Shop-ID",
                options=shop_ids_select_options
            )
            await ctx.send("Bitte wähle einen Shop aus, den du löschen möchtest:", components=shop_ids_selectmenu, ephemeral=True)


@bot.component("shop_id_select")
async def shop_id_select(ctx: dc.ComponentContext, value: list):
    shop_id = str(value[0])
    if not ctx.author.id == data["shop"]["shops"][shop_id]["owner"] or not user_is_privileged(ctx.author.roles):
        await ctx.send("Du bist nicht der Besitzer dieses Shops!", ephemeral=True)
        return
    shop_message = await ctx.channel.get_message(data["shop"]["shops"][shop_id]["message_id"])
    await shop_message.delete()
    if not data["shop"]["shops"][shop_id]["categorie"] in shop_categories_excluded_from_limit:
        data["shop"]["count"][str(ctx.author.id)] -= 1
    del data["shop"]["shops"][shop_id]
    json_dump(data)
    await ctx.edit("Der Shop wurde gelöscht.", components=[])


@bot.component("shop_abort")
async def shop_abort(ctx: dc.ComponentContext):
    shop_message_text = ctx.message.content
    identifier = int(
        re.match(r"\|\| (\d{4}) \|\|", shop_message_text).group(1))
    try:
        del shop_transfer_data[identifier]
    except KeyError:
        await ctx.edit("Es gibt keine aktive Shop-Erstellung. Bitte benutze keine Nachricht zweimal!", components=[])
        return
    await ctx.edit("Abgebrochen.", components=[])


@bot.component("categorie_select")
@dc.autodefer()
async def categorie_select(ctx: dc.ComponentContext, value: list):
    shop_message = ctx.message.content
    identifier = int(re.match(r"\|\| (\d{4}) \|\|", shop_message).group(1))
    if not str(ctx.author.id) in data["shop"]["count"]:
        data["shop"]["count"][str(ctx.author.id)] = 0
    elif not value[0] in shop_categories_excluded_from_limit:
        if data["shop"]["count"][str(ctx.author.id)] >= shop_count_limit:
            try:
                del shop_transfer_data[identifier]
            except KeyError:
                await ctx.edit("Ein Fehler ist aufgetreten. Bitte benutze eine Nachricht nicht zweimal!", components=[])
                return
            await ctx.edit("Du hast bereits die maximale Anzahl an Shops erreicht.", components=[])
            return
    try:
        shop_transfer_data[identifier]["categorie"] = value[0]
    except KeyError:
        await ctx.edit("Ein Fehler ist aufgetreten. Bitte benutze eine Nachricht nicht zweimal!", components=[])
        return
    shop_create_modal = dc.Modal(
        title="Shop erstellen",
        description="Hier kannst du einen Shop erstellen.",
        custom_id="shop_create",
        components=[
            dc.TextInput(
                    label="Name",
                    placeholder="Name",
                    custom_id="name",
                    style=dc.TextStyleType.SHORT,
                    required=True,
                    max_length=50
            ),
            dc.TextInput(
                label="Angebot",
                placeholder="Was bietest du an?",
                custom_id="offer",
                style=dc.TextStyleType.PARAGRAPH,
                required=True,
                max_length=250
            ),
            dc.TextInput(
                label="Ort",
                placeholder="Wo befindet sich dein Shop?",
                custom_id="location",
                style=dc.TextStyleType.PARAGRAPH,
                required=True,
                max_length=100
            ),
            dc.TextInput(
                label="DM-Beschreibung",
                placeholder="Was soll in der DM stehen?",
                custom_id="dm_description",
                style=dc.TextStyleType.PARAGRAPH,
                required=True,
                max_length=150
            )
        ]
    )
    await ctx.popup(shop_create_modal)


@bot.modal("shop_create")
async def mod_shop_create(ctx: dc.CommandContext, name: str, offer: str, location: str, dm_description: str):
    shop_message = ctx.message.content
    identifier = re.match(r"\|\| (\d{4}) \|\|", shop_message).group(1)
    data["shop"]["shops"][identifier] = {
        "name": name,
        "offer": offer,
        "location": location,
        "dm_description": dm_description,
        "categorie": shop_transfer_data[identifier]["categorie"],
        "owner": str(ctx.author.id),
        "approved": False
    }
    shop_embed = dc.Embed(
        title=name,
        description=f"""|| {shop_transfer_data[identifier]["categorie"]} ||\n
        **Angebot:**
        {offer}\n
        **Wo:**
        {location}\n
        **Besitzer:** {ctx.author.user.username}\n\
        Shop nicht genehmigt :x: """,
        color=0xdaa520,
        footer=dc.EmbedFooter(text=identifier)
    )
    sent_message = await ctx.channel.send(embeds=shop_embed)
    data["shop"]["shops"][identifier]["message_id"] = str(sent_message.id)
    if not shop_transfer_data[identifier]["categorie"] in shop_categories_excluded_from_limit:
        data["shop"]["count"][str(ctx.author.id)] += 1
    json_dump(data)
    del shop_transfer_data[identifier]
    await ctx.send("Shop erstellt.", ephemeral=True)


bot.start()
