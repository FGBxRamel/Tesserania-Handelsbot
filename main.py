import configparser as cp
import json
import re
from random import randint, shuffle
from time import localtime, mktime, sleep, strftime, strptime, time

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
                            "participants": []}, "shop": {"count": {}, "max_shop_count": 3, "shops": {}}}
for section, subsections in subsections.items():
    for subsection, value in subsections.items():
        if subsection not in data[section]:
            data[section][subsection] = value

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


@bot.command(
    name="button_test",
    description="Ein Test für Buttons.",
    scope=scope_ids
)
async def button_test(ctx: dc.CommandContext):
    button = dc.Button(
        label="Test",
        custom_id="test",
        style=dc.ButtonStyle.PRIMARY
    )
    button2 = dc.Button(
        label="Test2",
        custom_id="test2",
        style=dc.ButtonStyle.PRIMARY
    )
    button3 = dc.Button(
        label="Test3",
        custom_id="test3",
        style=dc.ButtonStyle.PRIMARY
    )
    button4 = dc.Button(
        label="Test4",
        custom_id="test4",
        style=dc.ButtonStyle.PRIMARY
    )
    selection = dc.SelectMenu(
        custom_id="test_select",
        placeholder="Ein Platzhalter",
        options=[
            dc.SelectOption(
                label="Testoption",
                value="Testoption 1",
                description="Eine Testoption"
            ),
            dc.SelectOption(
                label="testoption2",
                value="Testoption 2",
                description="Eine weitere Testoption"
            )
        ]
    )
    row = dc.ActionRow(
        components=[selection]
    )
    row2 = dc.ActionRow(
        components=[button]
    )
    await ctx.send("Test", components=[row, row2])


@ bot.component("test")
async def test_button(ctx: dc.ComponentContext):
    await ctx.send("Test", ephemeral=True)


@ bot.component("test2")
async def test2_button(ctx: dc.ComponentContext):
    await ctx.send("Test2", ephemeral=True)


@ bot.component("test3")
async def test3_button(ctx: dc.ComponentContext):
    await ctx.send("Test3", ephemeral=True)


@ bot.component("test4")
async def test4_button(ctx: dc.ComponentContext):
    await ctx.send("Test4", ephemeral=True)


@ bot.component("test_select")
async def test_select(ctx: dc.CommandContext, value):
    await ctx.edit("Du hast " + value[0] + " ausgewählt.", components=[])

categories = []
for category in data["shop"]["categories"]:
    categories.append(dc.SelectOption(
        label=category,
        value=category
    ))
categorie_select = dc.SelectMenu(
    custom_id="categorie_select",
    placeholder="Kategorie",
    options=categories,
    disabled=False
)
shop_abort_button = dc.Button(
    label="Abbrechen",
    custom_id="shop_abort",
    style=dc.ButtonStyle.DANGER
)


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
        )
    ]
)
async def shop(ctx: dc.CommandContext, aktion: str):
    if aktion == "create":
        if not str(ctx.author.id) in data["shop"]["count"]:
            data["shop"]["count"][str(ctx.author.id)] = 0
        elif data["shop"]["count"][str(ctx.author.id)] >= data["shop"]["max_shop_count"]:
            await ctx.send("Du hast bereits die maximale Anzahl an Shops erreicht.", ephemeral=True)
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


@bot.component("shop_abort")
async def shop_abort(ctx: dc.ComponentContext):
    await ctx.edit("Abgebrochen.", components=[], ephemeral=True)


@bot.component("categorie_select")
@dc.autodefer()
async def categorie_select(ctx: dc.ComponentContext, value):
    shop_message_text: str = ctx.message.content
    csv_string = re.match(r"\|\| (.*) \|\|", shop_message_text).group(0)
    shop_details = csv_string.split(",")
    identifier = randint(1000, 9999)
    while identifier in data["votings"]:
        identifier = randint(1000, 9999)
    data["shop"]["shops"][identifier] = {
        "name": shop_details[0],
        "offer": shop_details[1],
        "location": shop_details[2],
        "dm_description": shop_details[3],
        # TODO: Don't save the categorie as it's name, in case of change -> Admin Tools
        "categorie": value,
        "owner": str(ctx.author.id),
        "approved": False
    }
    shop_embed = dc.Embed(
        title=shop_details[0],
        description=f"""|| *{value}* ||\n\n
        **Angebot:**\n
        {shop_details[1]}\n\n
        **Wo:**\n
        {shop_details[2]}\n\n
        **Beseitzer:** {ctx.author.nick}\n\n
        Shop nicht genehmigt""" + r"\U000274C",
        color=0xdaa520,
        footer=dc.EmbedFooter(text=identifier)
    )
    json_dump(data)
    await ctx.channel.send(embeds=shop_embed)
    await ctx.edit("Der Shop wurde erstellt.", components=[], ephemeral=True)


@bot.modal("shop_create")
async def mod_shop_create(ctx: dc.ModalContext, name: str, offer: str, location: str, dm_description: str):
    row = dc.spread_to_rows([categorie_select, shop_abort_button])
    await ctx.send(f"""|| {name},{offer},{location},{dm_description} ||\n
    Bitte wähle eine Kategorie:""", components=row, ephemeral=True)


bot.start()
