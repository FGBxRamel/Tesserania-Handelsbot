import configparser as cp
from random import randint
import database as db
import sqlite3 as sql

import interactions as i

scope_ids = []


class ShopCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client: i.Client = client
        self.refresh_config()
        self.refresh_components()

    def refresh_config(self):
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            self.count_limit = config.getint('Shops', 'max_shops_per_person')
            self.categories = config.get('Shops', 'categories').split(',')
            self.categories = [category.strip()
                               for category in self.categories]
            self.categories_excluded_from_limit = config.get(
                'Shops', 'categories_excluded_from_limit').split(",")
            self.categories_excluded_from_limit = [
                category.strip() for category in self.categories_excluded_from_limit]
        global scope_ids
        scope_ids = config.get('IDs', 'server').split(',')
        self.transfer_data = {}
        self.privileged_roles_ids = [int(id) for id in config.get(
            'IDs', 'privileged_roles').split(',')]

    def refresh_components(self):
        options = []
        if len(self.categories) == 0:
            print("No categories found in config.ini!")
            return
        for category in self.categories:
            option = i.StringSelectOption(
                label=category,
                value=category
            )
            options.append(option)
        self.categorie_selectmenu = i.StringSelectMenu(
            custom_id="categorie_select",
            placeholder="Kategorie",
            *options
        )
        self.abort_button = i.Button(
            label="Abbrechen",
            custom_id="shop_abort",
            style=i.ButtonStyle.DANGER
        )

    @staticmethod
    def get_identifiers() -> list[str]:
        con = sql.connect("data.db")
        cur = con.cursor()
        cur.execute("SELECT shop_id FROM shops")
        return [str(ident[0]) for ident in cur.fetchall()]

    def get_shop_ids_select_options(self, user_id: int, user_roles: list[int]) -> list[i.StringSelectOption]:
        options = []
        priviliged = self.user_is_privileged(user_roles)
        if priviliged:
            shops = db.get_data("shops", fetch_all=True,
                                attribute="shop_id, name")
            for shop in shops:
                option = i.StringSelectOption(
                    label=shop[0],
                    value=str(shop[0]),
                    description=shop[1]
                )
                options.append(option)
        else:
            shops = db.get_data("shops", {"user_id": int(
                user_id)}, fetch_all=True, attribute="shop_id, name")
            for shop in shops:
                option = i.StringSelectOption(
                    label=str(shop[0]),
                    value=str(shop[0]),
                    description=shop[1]
                )
                options.append(option)
        return options

    def user_is_privileged(self, roles: list[int]) -> bool:
        return any(role in self.privileged_roles_ids for role in roles)

    @i.component_callback("shop_abort")
    async def shop_abort(self, ctx: i.ComponentContext):
        try:
            del self.transfer_data[int(ctx.author.id)]
        except KeyError:
            await ctx.edit("Es gibt keine aktive Shop-Erstellung. Bitte benutze keine Nachricht zweimal!", components=[])
            return
        await ctx.edit("Abgebrochen.", components=[])

    @i.slash_command(
        name="shop",
        description="Der Command für das Handelsregister.",
        scopes=scope_ids,
        options=[
            i.SlashCommandOption(
                name="aktion",
                description="Die Aktion, die du ausführen möchtest.",
                type=i.OptionType.STRING,
                required=True,
                choices=[
                    i.SlashCommandChoice(
                        name="eintragen",
                        value="create"
                    ),
                    i.SlashCommandChoice(
                        name="bearbeiten",
                        value="edit"
                    ),
                    i.SlashCommandChoice(
                        name="löschen",
                        value="delete"
                    ),
                    i.SlashCommandChoice(
                        name="durchsuchen",
                        value="search"
                    )
                ]
            )

        ]
    )
    async def shop(self, ctx: i.SlashContext, aktion: str):
        if aktion == "create":
            self.transfer_data[int(ctx.author.id)] = {}
            row1 = i.ActionRow(self.categorie_selectmenu)
            row2 = i.ActionRow(self.abort_button)
            sent_message = await ctx.send(components=[row1, row2], ephemeral=True)
            self.transfer_data[int(ctx.author.id)]["message_id"] = int(
                sent_message.id)
        elif aktion == "edit":
            options = self.get_shop_ids_select_options(
                int(ctx.user.id), ctx.member.roles)
            shop_ids_selectmenu = i.StringSelectMenu(
                custom_id="shop_edit_id_select",
                placeholder="Shop-ID",
                *options
            )
            await ctx.send("Bitte wähle einen Shop aus, den du bearbeiten möchtest:", components=shop_ids_selectmenu, ephemeral=True)
        elif aktion == "delete":
            options = self.get_shop_ids_select_options(
                int(ctx.user.id), ctx.member.roles)
            if len(options) == 0:
                await ctx.send("Du hast keine Shops, die du löschen könntest!", ephemeral=True)
                return
            shop_ids_selectmenu = i.StringSelectMenu(
                custom_id="shop_delete_id_select",
                placeholder="Shop-ID",
                *options,
                min_values=1,
                max_values=len(options)
            )
            await ctx.send("Bitte wähle einen Shop aus, den du löschen möchtest:", components=shop_ids_selectmenu, ephemeral=True)
        elif aktion == "search":
            options = [i.StringSelectOption(label=category, value=category)
                       for category in self.categories]
            category_selectmenu = i.StringSelectMenu(
                custom_id="shop_search_category_select",
                placeholder="Kategorie",
                *options,
                min_values=1,
                max_values=len(options)
            )
            await ctx.send("Bitte wähle die Kategorien aus, nach denen du suchen möchtest:", components=category_selectmenu, ephemeral=True)

    @ i.component_callback("shop_delete_id_select")
    async def shop_delete_id_select(self, ctx: i.ComponentContext):
        for shop_id in ctx.values:
            message_id = db.get_data(
                "shops", {"shop_id": int(shop_id)}, attribute="message_id")[0]
            shop_message = await ctx.channel.fetch_message(message_id)
            await shop_message.delete()
            category = db.get_data(
                "shops", {"shop_id": int(shop_id)}, attribute="category")[0]
            if category not in self.categories_excluded_from_limit:
                count = db.get_data("users", {"user_id": int(
                    ctx.author.id)}, attribute="shop_count")[0]
                db.update_data("users", "shop_count", count - 1,
                               {"user_id": int(ctx.author.id)})
            db.delete_data("shops", {"shop_id": int(shop_id)})
        await ctx.send(content="Die Shops wurden gelöscht.", ephemeral=True)

    @ i.component_callback("shop_edit_id_select")
    async def shop_edit_id_select(self, ctx: i.ComponentContext):
        shop_id = ctx.values[0]
        shop = db.get_data(
            "shops", {"shop_id": int(shop_id)}, attribute="name, offer, location, dm_description")
        components = [
            i.InputText(
                custom_id="id",
                label="ID (NICHT ÄNDERN!)",
                value=shop_id,
                style=i.TextStyles.SHORT,
                required=True
            ),
            i.InputText(
                custom_id="name",
                value=shop[0],
                label="Name",
                style=i.TextStyles.SHORT,
                placeholder="Name",
                required=True,
                max_length=50
            ),
            i.InputText(
                label="Angebot",
                placeholder="Was bietest du an?",
                custom_id="offer",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                max_length=250,
                value=shop[1]
            ),
            i.InputText(
                label="Ort",
                placeholder="Wo befindet sich dein Shop?",
                custom_id="location",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                max_length=100,
                value=shop[2]
            ),
            i.InputText(
                label="DM-Beschreibung",
                placeholder="Was soll in der DM stehen?",
                custom_id="dm_description",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                max_length=150,
                value=shop[3]
            )
        ]
        shop_modal = i.Modal(
            title="Shop bearbeiten",
            custom_id="shop_edit_modal",
            *components
        )
        await ctx.send_modal(shop_modal)

    @ i.modal_callback("shop_edit_modal")
    async def shop_edit_modal(self, ctx: i.ComponentContext, id: str, name: str, offer: str, location: str, dm_description: str):
        shop = db.get_data(
            "shops", {"shop_id": int(id)}, attribute="user_id, message_id")
        if shop is None:
            await ctx.edit("Du hast die ID verändert... Warum bist du so?")
            return
        if int(shop[0]) != int(ctx.author.id):
            await ctx.edit("Du kannst nur deine eigenen Shops bearbeiten!")
            return
        shop_message = await ctx.channel.fetch_message(shop[1])
        shop_embed: i.Embed = shop_message.embeds[0]
        shop_embed.fields[0] = i.EmbedField(
            name="Name", value=name, inline=False)
        shop_embed.fields[1] = i.EmbedField(
            name="Angebot", value=offer, inline=False)
        shop_embed.fields[2] = i.EmbedField(
            name="Ort", value=location, inline=False)
        shop_message = await shop_message.edit(embeds=shop_embed)
        db.update_data("shops", "name", name, {"shop_id": int(id)})
        db.update_data("shops", "offer", offer, {"shop_id": int(id)})
        db.update_data("shops", "location", location, {"shop_id": int(id)})
        db.update_data(
            "shops", "dm_description", dm_description, {"shop_id": int(id)})
        await ctx.send("Der Shop wurde erfolgreich bearbeitet!", ephemeral=True)

    @ i.component_callback("categorie_select")
    async def categorie_select(self, ctx: i.ComponentContext):
        value = ctx.values
        shop_count = db.get_data(
            "users", {"user_id": int(ctx.author.id)}, attribute="shop_count")
        if shop_count is None:
            db.save_data("users", "user_id, offers_count, shop_count",
                         (int(ctx.author.id), 0, 0))
            shop_count = 0
        else:
            shop_count = shop_count[0]
        if (
            not value[0] in self.categories_excluded_from_limit
            and shop_count >= self.count_limit
        ):
            try:
                del self.transfer_data[int(ctx.author.id)]
            except KeyError:
                await ctx.edit("Ein Fehler ist aufgetreten. Bitte benutze eine Nachricht nicht zweimal!", components=[])
                return
            await ctx.edit("Du hast bereits die maximale Anzahl an Shops erreicht.", components=[])
            return
        try:
            self.transfer_data[int(ctx.author.id)]["categorie"] = value[0]
        except KeyError:
            await ctx.edit("Ein Fehler ist aufgetreten. Bitte benutze eine Nachricht nicht zweimal!", components=[])
            return
        components = [
            i.InputText(
                label="Name",
                placeholder="Name",
                custom_id="name",
                style=i.TextStyles.SHORT,
                required=True,
                max_length=50
            ),
            i.InputText(
                label="Angebot",
                placeholder="Was bietest du an?",
                custom_id="offer",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                max_length=250
            ),
            i.InputText(
                label="Ort",
                placeholder="Wo befindet sich dein Shop?",
                custom_id="location",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                max_length=100
            ),
            i.InputText(
                label="DM-Beschreibung",
                placeholder="Was soll in der DM stehen?",
                custom_id="dm_description",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                max_length=150
            )
        ]
        shop_create_modal = i.Modal(
            title="Shop erstellen",
            custom_id="shop_create",
            *components
        )
        await ctx.send_modal(shop_create_modal)

    @ i.modal_callback("shop_create")
    async def mod_shop_create(self, ctx: i.SlashContext, name: str, offer: str, location: str, dm_description: str):
        identifier = str(randint(1000, 9999))
        identifiers = self.get_identifiers()
        while identifier in identifiers:
            identifier = str(randint(1000, 9999))
        shop_embed = i.Embed(
            title=name,
            description=f"""|| *{self.transfer_data[int(ctx.author.id)]["categorie"]}* ||\n""",
            color=0xdaa520,
            footer=i.EmbedFooter(text=str(identifier))
        )
        shop_embed.add_field(name="Angebot", value=offer, inline=False)
        shop_embed.add_field(name="Wo", value=location, inline=False)
        shop_embed.add_field(
            name="Besitzer", value=ctx.author.user.username, inline=False)
        shop_embed.add_field(name="Genehmigt", value=":x:", inline=False)
        sent_message = await ctx.channel.send(embeds=shop_embed)
        db.save_data("shops", "shop_id, user_id, name, offer, location, dm_description, category, message_id, approved", (identifier, int(
            ctx.author.id), name, offer, location, dm_description, self.transfer_data[int(ctx.author.id)]["categorie"], int(sent_message.id), False))
        if not self.transfer_data[int(ctx.author.id)]["categorie"] in self.categories_excluded_from_limit:
            count = db.get_data("users", {"user_id": int(
                ctx.author.id)}, attribute="shop_count")[0]
            db.update_data("users", "shop_count", count + 1,
                           {"user_id": int(ctx.author.id)})
        del self.transfer_data[int(ctx.author.id)]
        await ctx.send("Shop erstellt.", ephemeral=True)

    @ i.component_callback("shop_approve_id_select")
    async def shop_approve_id_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        for shop_id in ctx.values:
            shop = db.get_data(
                "shops", {"shop_id": int(shop_id)}, attribute="shop_id, message_id")
            db.update_data("shops", "approved", True,
                           {"shop_id": int(shop_id)})
            shop_message = await ctx.channel.fetch_message(int(shop[1]))
            shop_embed = shop_message.embeds[0]
            shop_embed.fields[3] = i.EmbedField(
                name="Genehmigt", value=":white_check_mark:", inline=False)
            await shop_message.edit(embeds=[shop_embed])
        await ctx.send("Shop(s) genehmigt.", ephemeral=True)

    @ i.component_callback("shop_deny_id_select")
    async def shop_deny_id_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        for shop_id in ctx.values:
            shop = db.get_data(
                "shops", {"shop_id": int(shop_id)}, attribute="shop_id, message_id")
            db.update_data("shops", "approved", False,
                           {"shop_id": int(shop_id)})
            shop_message = await ctx.channel.fetch_message(int(shop[1]))
            shop_embed = shop_message.embeds[0]
            shop_embed.fields[3] = i.EmbedField(
                name="Genehmigt", value=":x:", inline=False)
            await shop_message.edit(embeds=[shop_embed])
        await ctx.send("Shop(s) abgelehnt.", ephemeral=True)

    @i.component_callback("shop_search_category_select")
    async def shop_search_category_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        value = ctx.values
        shops_embed = i.Embed(
            title="Shops",
            description="Hier findest du alle Shops die den Kategorien entsprechen.",
            color=0xdaa520
        )
        shops = db.get_data("shops", {"category": value, "approved": True}, fetch_all=True,
                            attribute="name, category, dm_description")
        for name, category, dm_description in shops:
            dm_description = dm_description.replace("\\n", "\n")
            shops_embed.add_field(
                name=name,
                value=f"""|| *{category}* ||\n{dm_description}""",
                inline=False
            )
        await ctx.author.send(embeds=[shops_embed])
        await ctx.edit(content="Bitte schaue in deine DMs!", components=[])
