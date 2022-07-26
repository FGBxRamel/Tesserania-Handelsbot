import json
from tkinter.ttk import Style
from turtle import title
import interactions as dc
from random import randint
from time import strptime, time, strftime, localtime, mktime
from interactions.ext.get import get

bot = dc.Client(
    token="OTkzOTEyNTQ0NDcxMjk0MDUz.G0J-ya.5wMd30w_hydD_vR7j-DS1VRjQbQF4RRJVH-hH4")

scope_ids = [993913459169300540, 918559612813324340]
privileged_roles = ["918561303184965702", "918560437958742106"]
run = False

open("data.json", "a").close()


def implement(json: str):
    data = {}
    for key, value in json.items():
        if type(value) == dict and key in data:
            data[key] = implement(value, data[key])
        else:
            data[key] = value
    return data


def json_dump(data_dict: dict):
    with open("data.json", "w+") as dump_file:
        json.dump(data_dict, dump_file, indent=4)


global data
data = implement(json.loads(open("data.json", "r+").read()))
if not "offers" in data:
    data["offers"] = {}
if not "count" in data:
    data["count"] = {}
if not "votings" in data:
    data["votings"] = {}

async def automatic_delete() -> None:
    bot._loop.call_later(86400, run_delete)
    channel = await get(bot, dc.Channel, channel_id=988492568344014908)
    current_time = time()
    delete_ids = []
    global data
    for id, values in data["offers"].items():
        if values["deadline"] <= current_time:
            message = await channel.get_message(int(values["message_id"]))
            try:
                await message.delete("[Auto] Cleanup")
            except TypeError:
                continue
            delete_ids.append(id)
            data["count"][values["user_id"]] = data["count"][values["user_id"]] - 1
    for id in delete_ids:
        del data["offers"][id]
    json_dump(data)

def run_delete():
    bot._loop.create_task(automatic_delete())

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

#---Offer---

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
            custom_id="mod_edit_offer",
            components=[
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="ID des Angebots",
                    custom_id="edit_offer_id",
                    required=True,
                    min_length=4,
                    max_length=4
                ),
                dc.TextInput(
                    style=dc.TextStyleType.SHORT,
                    label="Titel",
                    custom_id="edit_offer_title",
                ),
                dc.TextInput(
                    style=dc.TextStyleType.PARAGRAPH,
                    label="Angebotstext",
                    custom_id="edit_offer_text"
                )
            ]
        )
        await ctx.popup(edit_id_modal)


@bot.modal("mod_create_offer")
async def create_offer_respone(ctx: dc.CommandContext, title: str, price: str, offer: str, deadline: str):
    identifier = randint(1000, 9999)
    while identifier in data["offers"]:
        identifier = randint(1000, 9999)
    data["offers"][str(identifier)] = {}
    data["offers"][str(identifier)]["user_id"] = str(ctx.author.id)
    data["offers"][str(identifier)]["price"] = str(price)
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
        description=f"\n**Angebot:** {offer}\n\n**Preis:** {price}",
        color=0xdaa520,
        author=dc.EmbedAuthor(
            name=f"{ctx.author.user.username}, {end_time} ({deadline} Tage)"),
        footer=dc.EmbedFooter(text=identifier)
    )
    channel = await ctx.get_channel()
    await ctx.send("", ephemeral=True)
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
    if not id in data["offers"]:
        await ctx.send("Diese ID existiert nicht!", ephemeral=True)
        return
    user_privilege = False
    for role in ctx.author.roles:
        if str(role) in privileged_roles:
            user_privilege = True
            break
    if not data["offers"][id]["user_id"] == str(ctx.author.id) and not user_privilege:
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
async def edit_offer_id(ctx: dc.CommandContext, id: str, title: str, text: str):
    try:
        int(id)
    except ValueError:
        await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
        return
    except BaseException as e:
        await ctx.send(
            f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
        return
    if not id in data["offers"]:
        await ctx.send("Diese ID existiert nicht!", ephemeral=True)
        return
    if not data["offers"][id]["user_id"] == str(ctx.author.id):
        await ctx.send("Du bist nicht berechtigt dieses Angebot zu bearbeiten!",
                       ephemeral=True)
        return
    offer_channel: dc.Channel = await ctx.get_channel()
    offer_message: dc.Message = await offer_channel.get_message(data["offers"][id]["message_id"])
    message_embed: dc.Embed = offer_message.embeds[0]
    if type(title) == None or title == " ":
        title = message_embed.title
    if type(text) == None or text == " ":
        text = message_embed.description
    text = f"{text}\n**Preis:** {data['offers'][id]['price']}\n*bearbeitet*"
    message_embed.title = title
    message_embed.description = text
    await offer_message.edit(embeds=message_embed)
    await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)


#---Abstimmungen---

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
                )
            ]
        )
    ]
)
async def votings(ctx : dc.CommandContext, aktion : str):
    if aktion == "create":
        if not str(ctx.author.id) in data["votings"]:
            data["votings"][str(ctx.author.id)] = {}
        create_voting_modal = dc.Modal(
            title="Abstimmung erstellen",
            custom_id = "mod_create_voting",
            components= [
                dc.TextInput(
                    style = dc.TextStyleType.PARAGRAPH,
                    label = "Welch Volksentscheid wollt ihr verkünden?",
                    custom_id = "create_voting_text",
                    required = True
                ),
                dc.TextInput(
                    style = dc.TextStyleType.SHORT,
                    label = "Wie viel Entscheidungen habt ihr zu bieten?",
                    custom_id = "create_voting_count",
                    required = True,
                    max_length = 2
                )
            ]
        )
        await ctx.popup(create_voting_modal)
    elif aktion == "delete":
        pass
    elif aktion == "edit":
        pass

@bot.modal("mod_create_voting")
async def create_voting_response(ctx : dc.CommandContext, text : str, count : str):
    pass