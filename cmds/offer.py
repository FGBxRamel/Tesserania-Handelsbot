import configparser as cp
import json
from os import makedirs, path
from time import strftime, time, localtime
from random import randint

import interactions as dc

scope_ids = []


class OfferCommand(dc.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.data_folder_path = 'data/offer/'
        self.data_file_path = self.data_folder_path + 'offer.json'
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
        with open("data.json", "w+") as data_file:
            # Do it so the main file knows where the offers are stored
            try:
                transfer_data = json.load(data_file)
            except json.decoder.JSONDecodeError as e:
                print(e)
                transfer_data = {}
            transfer_data["offer"] = {
                "data_file": self.data_file_path,
            }
            # TODO This doesn't save? WTF?
            json.dump(transfer_data, data_file, indent=4)

    def user_is_privileged(self, roles: list[int]) -> bool:
        return any(role in self.privileged_roles_ids for role in roles)

    @dc.extension_command(
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
    async def offer(self, ctx: dc.CommandContext, aktion: str, id: int = None):
        if aktion == "create":
            if not str(ctx.author.id) in self.data["count"]:
                self.data["count"][str(ctx.author.id)] = 0
            elif self.data["count"][str(ctx.author.id)] >= 3:
                await ctx.send("Es dürfen maximal drei Waren angeboten werden.", ephemeral=True)
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
            offer_options = []
            priviledged = self.user_is_privileged(ctx.author.roles)
            for id, offer_data in self.data["offers"].items():
                if offer_data["user_id"] == str(ctx.author.id) or priviledged:
                    offer_options.append(
                        dc.SelectOption(
                            label=id,
                            value=id,
                            description=offer_data["title"]
                        )
                    )
            delete_selectmenu = dc.SelectMenu(
                custom_id="delete_offer_menu",
                placeholder="Wähle ein Angebot aus",
                options=offer_options,
                min_values=1,
                max_values=3
            )
            await ctx.send("Wähle die Angebote aus, die du löschen möchtest.", components=delete_selectmenu, ephemeral=True)
        elif aktion == "edit":
            try:
                edit_id_modal = dc.Modal(
                    title="Angebot bearbeiten",
                    custom_id="mod_edit_offer",
                    components=[
                        dc.TextInput(
                            style=dc.TextStyleType.SHORT,
                            label="Titel",
                            custom_id="edit_offer_title",
                            value=self.data["offers"][str(
                                id)]["title"] if id else ""
                        ),
                        dc.TextInput(
                            style=dc.TextStyleType.PARAGRAPH,
                            label="Angebotstext",
                            custom_id="edit_offer_text",
                            value=self.data["offers"][str(
                                id)]["text"] if id else ""
                        ),
                        dc.TextInput(
                            style=dc.TextStyleType.SHORT,
                            label="ID des Angebots",
                            custom_id="edit_offer_id",
                            required=True,
                            min_length=4,
                            max_length=4,
                            value=str(id) if id else ""
                        )
                    ]
                )
            except KeyError:
                await ctx.send("Das Angebot existiert nicht.", ephemeral=True)
                return
            await ctx.popup(edit_id_modal)

    @dc.extension_modal("mod_create_offer")
    async def create_offer_respone(self, ctx: dc.CommandContext, title: str, price: str, offer_text: str, deadline: str):
        await ctx.send("Dein Angebot wird erstellt...", ephemeral=True)
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
        self.data["offers"][str(identifier)]["message_id"] = str(
            sent_message.id)
        self.data["count"][str(ctx.author.id)
                           ] = self.data["count"][str(ctx.author.id)] + 1
        self.save_data()
        await ctx.send("Das Angebot wurde entgegen genommen.", ephemeral=True)

    @dc.extension_component("delete_offer_menu")
    @dc.autodefer(ephemeral=True)
    async def delete_offer_response(self, ctx: dc.CommandContext, ids: list):
        offer_channel: dc.Channel = await ctx.get_channel()
        for id in ids:
            if id not in self.data["offers"]:
                await ctx.send(f"Die ID {id} existiert nicht!", ephemeral=True)
                return
            offer_message: dc.Message = await offer_channel.get_message(self.data["offers"][id]["message_id"])
            await offer_message.delete(reason=f"[Manuell] {ctx.author.user.username}")
            del self.data["offers"][id]
            self.data["count"][str(ctx.author.id)
                               ] = self.data["count"][str(ctx.author.id)] - 1
        self.save_data()
        await ctx.send("Die Angebote wurden gelöscht.", ephemeral=True)

    @dc.extension_modal("mod_edit_offer")
    async def edit_offer_id(self, ctx: dc.CommandContext, title: str, text: str, id: str = ""):
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
        offer_channel: dc.Channel = await ctx.get_channel()
        offer_message: dc.Message = await offer_channel.get_message(self.data["offers"][id]["message_id"])
        message_embed: dc.Embed = offer_message.embeds[0]
        if type(title) is None or title == " ":
            title = message_embed.title
        if type(text) is None or text == " ":
            text = message_embed.description + "\n*bearbeitet*"
        else:
            text = f"{text}\n**Preis:** {self.data['offers'][id]['price']}\n*bearbeitet*"
        message_embed.title = title
        message_embed.description = text
        self.data["offers"][id]["title"] = title
        self.data["offers"][id]["text"] = text
        self.save_data()
        await offer_message.edit(embeds=message_embed)
        await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)


def setup(client):
    OfferCommand(client)
