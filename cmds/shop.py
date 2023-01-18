import configparser as cp
import json
import re
from os import path, makedirs
from random import randint

import interactions as dc

scope_ids = []


class ShopCommand(dc.Extension):
    def __init__(self, client) -> None:
        self.client: dc.Client = client
        self.refresh_config()
        self.refresh_components()
        self.data_folder_path = "data/shop/"
        self.data_file_path = self.data_folder_path + "shop.json"
        self.load_data()

    def refresh_config(self):
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            self.count_limit = config.getint('Shops', 'max_shops_per_person')
            self.categories = config.get('Shops', 'categories').split(',')
            self.categories_excluded_from_limit = config.get(
                'Shops', 'categories_excluded_from_limit').split(",")
        global scope_ids
        scope_ids = config.get('IDs', 'server').split(',')
        self.transfer_data = {}
        self.privileged_roles_ids = [int(id) for id in config.get(
            'IDs', 'privileged_roles').split(',')]

    def refresh_components(self):
        categorie_options = []
        if len(self.categories) == 0:
            print("No categories found in config.ini!")
            return
        for category in self.categories:
            option = dc.SelectOption(
                label=category,
                value=category
            )
            categorie_options.append(option)
        self.categorie_selectmenu = dc.SelectMenu(
            custom_id="categorie_select",
            placeholder="Kategorie",
            options=categorie_options
        )
        self.abort_button = dc.Button(
            label="Abbrechen",
            custom_id="shop_abort",
            style=dc.ButtonStyle.DANGER
        )

    def save_data(self):
        with open(self.data_file_path, 'w+') as data_file:
            json.dump(self.data, data_file, indent=4)

    def load_data(self):
        try:
            with open(self.data_file_path, 'r') as data_file:
                self.data = json.load(data_file)
        except json.decoder.JSONDecodeError:
            self.setup_data_file()
        except FileNotFoundError:
            self.setup_data_file()

    def setup_data_file(self):
        if not path.exists(self.data_folder_path):
            makedirs(self.data_folder_path)
        if not path.exists(self.data_file_path):
            open(self.data_file_path, 'a').close()
        self.data = {
            "count": {},
            "shops": {}
        }
        self.save_data()

    def get_shop_ids_select_options(self, user_id: str, user_roles: list[int]) -> list[dc.SelectOption]:
        options = []
        priviliged = self.user_is_privileged(user_roles)
        for shop_id, shop_data in self.data["shops"].items():
            if shop_data["owner"] == user_id or priviliged:
                option = dc.SelectOption(
                    label=shop_id,
                    value=str(shop_id),
                    description=shop_data["name"]
                )
                options.append(option)
        return options

    def user_is_privileged(self, roles: list[int]) -> bool:
        return any(role in self.privileged_roles_ids for role in roles)

    @dc.extension_component("shop_abort")
    async def shop_abort(self, ctx: dc.ComponentContext):
        shop_message_text = ctx.message.content
        identifier = int(
            re.match(r"\|\| (\d{4}) \|\|", shop_message_text).group(1))
        try:
            del self.transfer_data[identifier]
        except KeyError:
            await ctx.edit("Es gibt keine aktive Shop-Erstellung. Bitte benutze keine Nachricht zweimal!", components=[])
            return
        await ctx.edit("Abgebrochen.", components=[])

    @dc.extension_command(
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
    async def shop(self, ctx: dc.CommandContext, aktion: str, id: str = None):
        if id:
            try:
                int(id)
                id = str(id)
            except ValueError:
                await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
                return
        if aktion == "create":
            identifier = str(randint(1000, 9999))
            while identifier in self.data["shops"] or identifier in self.transfer_data:
                identifier = str(randint(1000, 9999))
            self.transfer_data[identifier] = {}
            row1 = dc.ActionRow(components=[self.categorie_selectmenu])
            row2 = dc.ActionRow(components=[self.abort_button])
            sent_message = await ctx.send(f"""|| {identifier} ||
            Bitte wähle eine Kategorie:""", components=[row1, row2], ephemeral=True)
            self.transfer_data[identifier]["message_id"] = sent_message.id
        elif aktion == "edit":
            # TODO Make this work
            await ctx.send("Dieser Command ist noch nicht verfügbar.", ephemeral=True)
        elif aktion == "delete":
            shop_ids_select_options = self.get_shop_ids_select_options()
            shop_ids_selectmenu = dc.SelectMenu(
                custom_id="shop_delete_id_select",
                placeholder="Shop-ID",
                options=shop_ids_select_options
            )
            await ctx.send("Bitte wähle einen Shop aus, den du löschen möchtest:", components=shop_ids_selectmenu, ephemeral=True)

    @dc.extension_component("shop_delete_id_select")
    async def shop_delete_id_select(self, ctx: dc.ComponentContext, value: list):
        shop_id = str(value[0])
        shop_message = await ctx.channel.get_message(self.data["shops"][shop_id]["message_id"])
        await shop_message.delete()
        if not self.data["shops"][shop_id]["categorie"] in self.categories_excluded_from_limit:
            self.data["count"][str(ctx.author.id)] -= 1
        del self.data["shops"][shop_id]
        self.save_data()
        await ctx.edit("Der Shop wurde gelöscht.", components=[])

    @dc.extension_component("categorie_select")
    @dc.autodefer()
    async def categorie_select(self, ctx: dc.ComponentContext, value: list):
        shop_message = ctx.message.content
        identifier = re.match(r"\|\| (\d{4}) \|\|", shop_message).group(1)
        if not str(ctx.author.id) in self.data["count"]:
            self.data["count"][str(ctx.author.id)] = 0
        elif not value[0] in self.categories_excluded_from_limit:
            if self.data["count"][str(ctx.author.id)] >= self.count_limit:
                try:
                    del self.transfer_data[identifier]
                except KeyError:
                    await ctx.edit("Ein Fehler ist aufgetreten. Bitte benutze eine Nachricht nicht zweimal!", components=[])
                    return
                await ctx.edit("Du hast bereits die maximale Anzahl an Shops erreicht.", components=[])
                return
        try:
            self.transfer_data[identifier]["categorie"] = value[0]
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

    @dc.extension_modal("shop_create")
    async def mod_shop_create(self, ctx: dc.CommandContext, name: str, offer: str, location: str, dm_description: str):
        shop_message = ctx.message.content
        identifier = re.match(r"\|\| (\d{4}) \|\|", shop_message).group(1)
        self.data["shops"][identifier] = {
            "name": name,
            "offer": offer,
            "location": location,
            "dm_description": dm_description,
            "categorie": self.transfer_data[identifier]["categorie"],
            "owner": str(ctx.author.id),
            "approved": False
        }
        shop_embed = dc.Embed(
            title=name,
            description=f"""|| {self.transfer_data[identifier]["categorie"]} ||\n
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
        self.data["shops"][identifier]["message_id"] = str(sent_message.id)
        if not self.transfer_data[identifier]["categorie"] in self.categories_excluded_from_limit:
            self.data["count"][str(ctx.author.id)] += 1
        self.save_data()
        del self.transfer_data[identifier]
        await ctx.send("Shop erstellt.", ephemeral=True)


def setup(client):
    ShopCommand(client)
