import configparser as cp
import json
from random import randint
from time import localtime, mktime, strftime, strptime, time

import interactions as dc
from interactions.ext.get import get

with open('config.ini', 'r') as config_file:
    config = cp.ConfigParser()
    config.read_file(config_file)

    TOKEN = config.get('General', 'token')
    server_ids = config.get('IDs', 'server').split(',')
    privileged_roles_ids = [int(id) for id in config.get(
        'IDs', 'privileged_roles').split(',')]
    offer_channel_id = int(config.get('IDs', 'offer_channel'))
    voting_channel_id = int(config.get('IDs', 'voting_channel'))
    voting_role_to_ping_id = int(config.get('IDs', 'voting_role_to_ping'))


bot = dc.Client(
    token=TOKEN)

scope_ids = server_ids
run = False
emote_chars = ["\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9", "\U0001F1EA",
               "\U0001F1EB", "\U0001F1EC", "\U0001F1ED", "\U0001F1EE", "\U0001F1EF"]

open("data.json", "a").close()


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
if "offers" not in data:
    data["offers"] = {}
if "count" not in data:
    data["count"] = {}
if "votings" not in data:
    data["votings"] = {}
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
        )
    ]
)
async def offer(ctx: dc.CommandContext, aktion: str):
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
                    max_length=4
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
                    value=data["offers"][str(id)]["title"]
                ),
                dc.TextInput(
                    style=dc.TextStyleType.PARAGRAPH,
                    label="Angebotstext",
                    custom_id="edit_offer_text",
                    value=data["offers"][str(id)]["text"]
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
    await ctx.send("Das Angebot wurde entgegen genommen.", ephemeral=True)
    sent_message = await channel.send(embeds=app_embed)
    data["offers"][str(identifier)]["message_id"] = str(sent_message.id)
    data["count"][str(ctx.author.id)] = data["count"][str(ctx.author.id)] + 1
    json_dump(data)


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
        )
    ]
)
async def votings(ctx: dc.CommandContext, aktion: str):
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
                    max_length=4
                )
            ]
        )
        await ctx.popup(delete_modal)
    elif aktion == "edit":
        if id is None:
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
                        max_length=4
                    ),
                    dc.TextInput(
                        style=dc.TextStyleType.PARAGRAPH,
                        label="Abstimmungstext",
                        custom_id="edit_voting_text",
                        required=True
                    )
                ]
            )
        else:
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
                        value=str(id)
                    ),
                    dc.TextInput(
                        style=dc.TextStyleType.PARAGRAPH,
                        label="Abstimmungstext",
                        custom_id="edit_voting_text",
                        required=True,
                        value=data["votings"][str(id)]["text"]
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
                    max_length=4
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
    await ctx.send("Die Abstimmung wurde entgegen genommen.", ephemeral=True)
    sent_message = await channel.send(content=voting_role_to_ping.mention, embeds=voting_embed)
    emote_index = 0
    while int(count) > emote_index:
        await sent_message.create_reaction(emote_chars[emote_index])
        emote_index += 1
    data["votings"][str(identifier)]["message_id"] = str(sent_message.id)
    json_dump(data)


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
