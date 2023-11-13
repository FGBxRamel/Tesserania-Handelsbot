import configparser as cp
from random import randint
import classes.database as db
from classes.shop import Shop
import sqlite3 as sql

import interactions as i
from interactions.ext.paginators import Paginator

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
        scope_ids = config.get('General', 'servers').split(',')
        self.transfer_data = {}

    def refresh_components(self):
        options = []
        if len(self.categories) == 0:
            raise ValueError("No categories found in config.ini!")
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

    @staticmethod
    def get_shop_ids_select_options(user_id: int) -> list[i.StringSelectOption]:
        options = []
        shops = db.get_data("shops", fetch_all=True,
                            attribute="shop_id, name, owners")
        for shop in shops:
            if str(user_id) in shop[2]:
                option = i.StringSelectOption(
                    label=str(shop[0]),
                    value=str(shop[0]),
                    description=shop[1]
                )
                options.append(option)
        return options

    @i.component_callback("shop_abort")
    async def shop_abort(self, ctx: i.ComponentContext):
        try:
            del self.transfer_data[int(ctx.author.id)]
        except KeyError:
            await ctx.send(content="Es gibt keine aktive Shop-Erstellung. Bitte benutze keine Nachricht zweimal!",
                           ephemeral=True, delete_after=5)
            return
        await ctx.send(content="Abgebrochen.",
                       ephemeral=True, delete_after=5)

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
            sent_message = await ctx.send(components=[row1, row2], ephemeral=True, delete_after=20)
            self.transfer_data[int(ctx.author.id)]["message_id"] = int(
                sent_message.id)
        elif aktion == "edit":
            options = self.get_shop_ids_select_options(
                int(ctx.user.id))
            shop_ids_selectmenu = i.StringSelectMenu(
                custom_id="shop_edit_id_select",
                placeholder="Shop-ID",
                *options
            )
            await ctx.send("Bitte wähle einen Shop aus, den du bearbeiten möchtest:",
                           components=shop_ids_selectmenu, ephemeral=True, delete_after=15)
        elif aktion == "delete":
            options = self.get_shop_ids_select_options(
                int(ctx.user.id))
            if len(options) == 0:
                await ctx.send("Du hast keine Shops, die du löschen könntest!", ephemeral=True,
                               delete_after=5)
                return
            shop_ids_selectmenu = i.StringSelectMenu(
                custom_id="shop_delete_id_select",
                placeholder="Shop-ID",
                *options,
                min_values=1,
                max_values=len(options)
            )
            await ctx.send("Bitte wähle einen Shop aus, den du löschen möchtest:",
                           components=shop_ids_selectmenu, ephemeral=True, delete_after=15)
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
            await ctx.send("Bitte wähle die Kategorien aus, nach denen du suchen möchtest:",
                           components=category_selectmenu, ephemeral=True, delete_after=15)

    @ i.component_callback("shop_delete_id_select")
    async def shop_delete_id_select(self, ctx: i.ComponentContext):
        for shop_id in ctx.values:
            await Shop(int(shop_id), self.client, ctx.channel).delete()
        await ctx.send(content="Die Shops wurden gelöscht.", ephemeral=True, delete_after=5)

    @ i.component_callback("shop_edit_id_select")
    async def shop_edit_id_select(self, ctx: i.ComponentContext):
        shop_id = ctx.values[0]
        shop = Shop(int(shop_id), self.client, ctx.channel)
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
                value=shop.name,
                label="Name",
                style=i.TextStyles.SHORT,
                placeholder="Name",
                required=True
            ),
            i.InputText(
                label="Angebot",
                placeholder="Was bietest du an?",
                custom_id="offer",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                value=shop.offer
            ),
            i.InputText(
                label="Ort",
                placeholder="Wo befindet sich dein Shop?",
                custom_id="location",
                style=i.TextStyles.PARAGRAPH,
                required=True,
                value=shop.location
            )
        ]
        shop_modal = i.Modal(
            title="Shop bearbeiten",
            custom_id="shop_edit_modal",
            *components
        )
        await ctx.send_modal(shop_modal)

    @ i.modal_callback("shop_edit_modal")
    async def shop_edit_modal(self, ctx: i.ComponentContext, id: str, name: str, offer: str, location: str):
        try:
            shop = Shop(int(id), self.client, ctx.channel)
        except ValueError:
            await ctx.send(content="Du hast die ID verändert... Warum bist du so?",
                           ephemeral=True, delete_after=5)
            return
        if int(ctx.author.id) not in shop.owners:
            await ctx.send(content="Du kannst nur deine eigenen Shops bearbeiten!",
                           ephemeral=True, delete_after=5)
            return
        shop.name = name
        shop.offer = offer
        shop.location = location
        await shop.update()
        await ctx.send("Der Shop wurde erfolgreich bearbeitet!", ephemeral=True, delete_after=5)

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
                await ctx.send(content="Ein Fehler ist aufgetreten. Bitte benutze eine Nachricht nicht zweimal!",
                               ephemeral=True, delete_after=5)
                return
            await ctx.send(content="Du hast bereits die maximale Anzahl an Shops erreicht.",
                           ephemeral=True, delete_after=5)
            return
        identifier = str(randint(1000, 9999))
        identifiers = self.get_identifiers()
        while identifier in identifiers:
            identifier = str(randint(1000, 9999))
        shop = Shop(int(identifier), self.client, ctx.channel,
                    skip_setup=True,
                    category=value[0]
                    )
        try:
            self.transfer_data[int(ctx.author.id)] = shop
        except KeyError:
            await ctx.send(content="Ein Fehler ist aufgetreten. Bitte benutze eine Nachricht nicht zweimal!",
                           ephemeral=True, delete_after=5)
            return
        components = [
            i.InputText(
                label="Name",
                placeholder="Name",
                custom_id="name",
                style=i.TextStyles.SHORT,
                required=True
            ),
            i.InputText(
                label="Angebot",
                placeholder="Was bietest du an?",
                custom_id="offer",
                style=i.TextStyles.PARAGRAPH,
                required=True
            ),
            i.InputText(
                label="Ort",
                placeholder="Wo befindet sich dein Shop?",
                custom_id="location",
                style=i.TextStyles.PARAGRAPH,
                required=True
            )
        ]
        shop_create_modal = i.Modal(
            title="Shop erstellen",
            custom_id="shop_create",
            *components
        )
        await ctx.send_modal(shop_create_modal)

    @ i.modal_callback("shop_create")
    async def mod_shop_create(self, ctx: i.ModalContext, name: str, offer: str, location: str):
        shop: Shop = self.transfer_data[int(ctx.author.id)]
        shop.set_name(name)
        shop.set_offer(offer)
        shop.set_location(location)
        self.transfer_data[int(ctx.author.id)] = shop
        user_select = i.UserSelectMenu(
            custom_id="shop_create_user_select",
            placeholder="Bitte wähle die Besitzer aus (dich inkl.)",
            min_values=1,
            max_values=25,
        )
        await ctx.send(components=user_select, ephemeral=True, delete_after=25)

    @i.component_callback("shop_search_category_select")
    async def shop_search_category_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        value = ctx.values
        embeds = []
        shops = db.get_data("shops", {"category": value, "approved": True}, fetch_all=True,
                            attribute="shop_id")
        for shop_id in shops:
            shop = Shop(int(shop_id[0]), self.client, ctx.channel)
            embed = await shop.get_embed()
            embeds.append(embed)
        paginator = Paginator.create_from_embeds(self.client, *embeds)
        paginator.show_select_menu = True
        await paginator.send(ctx, **{"ephemeral": True})
        await ctx.send(content="Have fun!", delete_after=3, ephemeral=True)

    @i.component_callback("shop_create_user_select")
    async def shop_create_user_select(self, ctx: i.ComponentContext):
        shop: Shop = self.transfer_data[int(ctx.author.id)]
        owners = []
        for user in ctx.values:
            owners.append(int(user.id))
        shop.set_owners(owners)
        await shop.create()
        await ctx.send("Der Shop wurde erfolgreich erstellt!", ephemeral=True, delete_after=5)
