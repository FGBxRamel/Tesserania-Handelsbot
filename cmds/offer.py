import configparser as cp
import json
from os import makedirs, path
from time import strftime, time, localtime
from random import randint

import interactions as i

scope_ids = []


class OfferCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.data_folder_path = 'data/offer/'
        self.data_file_path = self.data_folder_path + 'offer.json'
        self.data = {}
        self.refresh_config()
        self.setup_data()

    def refresh_config(self):
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            global scope_ids
            scope_ids = config.get('IDs', 'server').split(',')
            self.privileged_roles_ids = [int(id) for id in config.get(
                'IDs', 'privileged_roles').split(',')]

    def save_data(self):
        with open(self.data_file_path, 'w+') as data_file:
            json.dump(self.data, data_file, indent=4)

    def load_data(self):
        with open(self.data_file_path, 'r') as data_file:
            self.data = json.load(data_file)

    def setup_data(self):
        def create_data_file():
            open(self.data_file_path, 'a').close()
            self.data = {
                "offers": {},
                "count": {}
            }
            self.save_data()
        if not path.exists(self.data_folder_path):
            makedirs(self.data_folder_path)
        if path.exists(self.data_file_path):
            try:
                self.load_data()
            except json.decoder.JSONDecodeError:
                create_data_file()
        else:
            create_data_file()
        with open("data.json", "r") as data_file:
            try:
                transfer_data = json.load(data_file)
            except json.decoder.JSONDecodeError as e:
                print(e)
                transfer_data = {}
        with open("data.json", "w") as data_file:
            # Do it so the main file knows where the offers are stored
            transfer_data["offer"] = {
                "data_file": self.data_file_path,
            }
            json.dump(transfer_data, data_file, indent=4)

    def user_is_privileged(self, roles: list[int]) -> bool:
        return any(role in self.privileged_roles_ids for role in roles)

    @i.slash_command(
        name="angebot",
        description="Der Befehl für Angebote.",
        scopes=scope_ids,
        options=[
            i.SlashCommandOption(
                name="aktion",
                description="Das, was du tuen willst.",
                type=i.OptionType.STRING,
                required=True,
                choices=[
                    i.SlashCommandChoice(
                        name="erstellen",
                        value="create"
                    ),
                    i.SlashCommandChoice(
                        name="löschen",
                        value="delete"
                    ),
                    i.SlashCommandChoice(
                        name="bearbeiten",
                        value="edit"
                    )
                ]
            )
        ]
    )
    async def offer(self, ctx: i.SlashContext, aktion: str):
        if aktion == "create":
            if not str(ctx.author.id) in self.data["count"]:
                self.data["count"][str(ctx.author.id)] = 0
            elif self.data["count"][str(ctx.author.id)] >= 3:
                await ctx.send("Es dürfen maximal drei Waren angeboten werden.", ephemeral=True)
                return
            create_modal = i.Modal(
                title="Angebot erstellen",
                custom_id="mod_create_offer",
                components=[
                    i.TextInput(
                        style=i.TextStyleType.SHORT,
                        label="Titel",
                        custom_id="create_offer_title",
                        required=True
                    ),
                    i.TextInput(
                        style=i.TextStyleType.SHORT,
                        label="Preis",
                        custom_id="create_offer_price",
                        value="VB"
                    ),
                    i.TextInput(
                        style=i.TextStyleType.PARAGRAPH,
                        label="Was bietest du an?",
                        custom_id="create_offer_text",
                        required=True
                    ),
                    i.TextInput(
                        style=i.TextStyleType.SHORT,
                        label="Wie lange läuft das Angebot? (1-7)",
                        custom_id="create_offer_deadline",
                        required=True,
                        max_length=1
                    )
                ]
            )
            await ctx.popup(create_modal)
        elif aktion == "delete":
            priviledged = self.user_is_privileged(ctx.author.roles)
            offer_options = []
            for offer_id, offer_data in self.data["offers"].items():
                if offer_data["user_id"] == str(ctx.author.id) or priviledged:
                    offer_options.append(
                        i.StringSelectOption(
                            label=offer_id,
                            value=offer_id,
                            description=offer_data["title"]
                        )
                    )
            if len(offer_options) == 0:
                await ctx.send("Du hast keine Angebote, die du löschen kannst.", ephemeral=True)
                return
            delete_selectmenu = i.StringSelectMenu(
                custom_id="delete_offer_menu",
                placeholder="Wähle ein Angebot aus",
                options=offer_options,
                min_values=1,
                max_values=len(offer_options)
            )
            await ctx.send("Wähle die Angebote aus, die du löschen möchtest.", components=delete_selectmenu, ephemeral=True)
        elif aktion == "edit":
            offer_options = []
            for offer_id, offer_data in self.data["offers"].items():
                offer_options.append(
                    i.StringSelectOption(
                        label=offer_id,
                        value=offer_id,
                        description=offer_data["title"]
                    )
                )
            if len(offer_options) == 0:
                await ctx.send("Es gibt keine Angebote, die du bearbeiten kannst.", ephemeral=True)
                return
            edit_selectmenu = i.StringSelectMenu(
                custom_id="edit_offer_menu",
                placeholder="Wähle ein Angebot aus",
                options=offer_options,
                min_values=1,
                max_values=1
            )
            await ctx.send("Wähle das Angebot aus, das du bearbeiten möchtest.", components=edit_selectmenu, ephemeral=True)

    @i.modal_callback("mod_create_offer")
    async def create_offer_respone(self, ctx: i.SlashContext, title: str, price: str, offer_text: str, deadline: str):
        identifier = randint(1000, 9999)
        while identifier in self.data["offers"]:
            identifier = randint(1000, 9999)
        self.data["offers"][str(identifier)] = {
            "title": str(title),
            "user_id": str(ctx.author.id),
            "price": str(price),
            "text": str(offer_text)
        }
        if int(deadline) < 1:
            deadline = 1
        elif int(deadline) > 7:
            deadline = 7
        # The deadline is: current_time_seconds_epoch + x * seconds_of_one_day
        end_time = time() + int(deadline) * 86400
        self.data["offers"][str(identifier)]["deadline"] = end_time
        end_time = strftime("%d.%m.") + "- " + \
            strftime("%d.%m.", localtime(end_time))
        app_embed = i.Embed(
            title=title,
            description=f"\n{offer_text}\n\n**Preis:** {price}",
            color=0xdaa520,
            author=i.EmbedAuthor(
                name=f"{ctx.user.username}, {end_time} ({deadline} Tage)"),
            footer=i.EmbedFooter(text=identifier)
        )
        channel = await ctx.get_channel()
        sent_message = await channel.send(embeds=app_embed)
        self.data["offers"][str(identifier)]["message_id"] = str(
            sent_message.id)
        self.data["count"][str(ctx.author.id)
                           ] = self.data["count"][str(ctx.author.id)] + 1
        self.save_data()
        await ctx.send("Das Angebot wurde entgegen genommen.", ephemeral=True)

    @i.component_callback("delete_offer_menu")
    async def delete_offer_response(self, ctx: i.SlashContext, ids: list):
        await ctx.defer(ephemeral=True)
        offer_channel: i.Channel = await ctx.get_channel()
        for id in ids:
            offer_message: i.Message = await offer_channel.get_message(self.data["offers"][id]["message_id"])
            await offer_message.delete(reason=f"[Manuell] {ctx.author.user.username}")
            del self.data["offers"][id]
            self.data["count"][str(ctx.author.id)
                               ] = self.data["count"][str(ctx.author.id)] - 1
        self.save_data()
        await ctx.send("Die Angebote wurden gelöscht.", ephemeral=True)

    @i.component_callback("edit_offer_menu")
    async def edit_offer_response(self, ctx: i.SlashContext, ids: list):
        edit_modal = i.Modal(
            title="Angebot bearbeiten",
            custom_id="mod_edit_offer",
            description="Bearbeite das Angebot",
            components=[
                i.TextInput(
                    style=i.TextStyleType.SHORT,
                    label="Titel",
                    custom_id="edit_offer_title",
                    required=True,
                    value=self.data["offers"][ids[0]]["title"]
                ),
                i.TextInput(
                    style=i.TextStyleType.PARAGRAPH,
                    label="Text",
                    custom_id="edit_offer_text",
                    required=True,
                    value=self.data["offers"][ids[0]]["text"]
                ),
                i.TextInput(
                    style=i.TextStyleType.SHORT,
                    label="ID",
                    custom_id="edit_offer_id",
                    required=True,
                    max_length=4,
                    value=ids[0]
                )
            ]
        )
        await ctx.popup(edit_modal)

    @i.modal_callback("mod_edit_offer")
    async def edit_offer_id(self, ctx: i.SlashContext, title: str, text: str, id: str = ""):
        try:
            int(id)
        except ValueError:
            await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
            return
        except BaseException as e:
            await ctx.send(
                f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
            return
        if id not in self.data["offers"]:
            await ctx.send("Diese ID existiert nicht!", ephemeral=True)
            return
        if not self.data["offers"][id]["user_id"] == str(ctx.author.id):
            await ctx.send("Du bist nicht berechtigt dieses Angebot zu bearbeiten!",
                           ephemeral=True)
            return
        self.data["offers"][id]["title"] = title
        self.data["offers"][id]["text"] = text
        offer_channel: i.Channel = await ctx.get_channel()
        offer_message: i.Message = await offer_channel.get_message(self.data["offers"][id]["message_id"])
        message_embed: i.Embed = offer_message.embeds[0]
        text = f"{text}\n**Preis:** {self.data['offers'][id]['price']}\n*bearbeitet*"
        message_embed.title = title
        message_embed.description = text
        await offer_message.edit(embeds=message_embed)
        self.save_data()
        await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)

