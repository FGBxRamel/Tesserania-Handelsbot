import configparser as cp
import pkgutil
from random import randint
import classes.database as db
from classes.shop import Shop
import sqlite3 as sql

import interactions as i

scope_ids = []


class AdminCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.transfer_data = {}
        self.refresh_config()

    def refresh_config(self) -> None:
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            global scope_ids
            scope_ids = config.get('General', 'servers').split(',')
            self.shop_categories = config.get('Shops', 'categories').split(',')
            self.shop_categories = [category.strip()
                                    for category in self.shop_categories]

    @staticmethod
    def get_shop_identifiers() -> list[str]:
        con = sql.connect("data.db")
        cur = con.cursor()
        cur.execute("SELECT shop_id FROM shops")
        return [str(ident[0]) for ident in cur.fetchall()]

    def reload_extensions(self) -> None:
        extension_names = [
            m.name for m in pkgutil.iter_modules(["cmds"], prefix="cmds.")]
        for extension in extension_names:
            self.client.reload_extension(extension)

    @i.slash_command(
        name="admin",
        description="Admin commands",
        scopes=scope_ids
    )
    async def admin_base(self, ctx: i.SlashContext) -> None:
        pass

    @admin_base.subcommand(
        sub_cmd_name="shop",
        sub_cmd_description="Shop Command",
        options=[
            i.SlashCommandOption(
                name="aktion",
                description="Was soll gemacht werden?",
                required=True,
                type=i.OptionType.STRING,
                choices=[
                    i.SlashCommandChoice(name="genehmigen", value="approve"),
                    i.SlashCommandChoice(name="ablehnen", value="deny"),
                    i.SlashCommandChoice(name="erstellen", value="create"),
                    i.SlashCommandChoice(name="bearbeiten", value="edit"),
                    i.SlashCommandChoice(name="besitzer", value="owner"),
                    i.SlashCommandChoice(name="pflicht", value="obligatory"),
                    i.SlashCommandChoice(name="freiwillig", value="voluntary")
                ]
            )
        ]
    )
    async def admin_shop(self, ctx: i.SlashContext, aktion: str) -> None:
        if aktion == "approve":
            options = []
            shops = db.get_data("shops", {"approved": False}, fetch_all=True,
                                attribute="shop_id, name")
            if shops == []:
                await ctx.send("Es gibt keine Shops, die noch nicht genehmigt wurden.", ephemeral=True)
                return
            for shop_id, name in shops:
                options.append(i.StringSelectOption(
                    label=shop_id,
                    description=name,
                    value=shop_id
                ))
            menus = []
            for j in range(0, len(options) // 25 + 1):
                menus.append(
                    i.StringSelectMenu(
                        custom_id=f"shop_approve_id_select_{j}",
                        placeholder="Wähle die Shops aus die du genehmigen möchtest.",
                        *options[j*25:(j+1)*25],
                        min_values=1,
                        max_values=len(options[j*25:(j+1)*25])
                    )
                )
            for menu in menus:
                await ctx.send(components=menu, ephemeral=True, delete_after=25, silent=True)
        elif aktion == "deny":
            options = []
            shops = db.get_data("shops", {"approved": True}, fetch_all=True,
                                attribute="shop_id, name")
            if shops is None or len(shops) == 0:
                await ctx.send("Es gibt keine genehmigten Shops.", ephemeral=True)
                return
            for shop_id, name in shops:
                options.append(i.StringSelectOption(
                    label=shop_id,
                    description=name,
                    value=shop_id
                ))
            menus = []
            for j in range(0, len(options) // 25 + 1):
                menus.append(
                    i.StringSelectMenu(
                        custom_id=f"shop_deny_id_select_{j}",
                        placeholder="Shop-ID",
                        *options[j*25:(j+1)*25],
                        min_values=1,
                        max_values=len(options[j*25:(j+1)*25])
                    )
                )
            for menu in menus:
                await ctx.send(components=menu, ephemeral=True, delete_after=25, silent=True)
        elif aktion == "create":
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
                custom_id="admin_shop_create",
                *components
            )
            await ctx.send_modal(shop_create_modal)
        elif aktion == "edit":
            options = []
            shops = db.get_data("shops", fetch_all=True,
                                attribute="shop_id, name")
            if shops == []:
                await ctx.send("Es gibt keine Shops.", ephemeral=True, delete_after=5)
                return
            for shop_id, name in shops:
                options.append(i.StringSelectOption(
                    label=shop_id,
                    description=name,
                    value=shop_id
                ))
                menus = []
            for j in range(0, len(options) // 25 + 1):
                menus.append(
                    i.StringSelectMenu(
                        custom_id=f"admin_shop_edit_id_select_{j}",
                        placeholder="Shop-ID",
                        *options[j*25:(j+1)*25]
                    )
                )
            for menu in menus:
                await ctx.send(components=menu, ephemeral=True, delete_after=25, silent=True)
        elif aktion == "owner":
            shops = db.get_data("shops", fetch_all=True,
                                attribute="shop_id, name")
            if shops == []:
                await ctx.send("Es gibt keine Shops.", ephemeral=True, delete_after=5)
                return
            options = []
            for shop_id, name in shops:
                options.append(i.StringSelectOption(
                    label=shop_id,
                    description=name,
                    value=shop_id
                ))
            menus = []
            for j in range(0, len(options) // 25 + 1):
                menus.append(
                    i.StringSelectMenu(
                        custom_id=f"admin_shop_owner_select_shop_{j}",
                        placeholder="Shop-ID",
                        *options[j*25:(j+1)*25]
                    )
                )
            for menu in menus:
                await ctx.send(components=menu, ephemeral=True, delete_after=25, silent=True)
        elif aktion == "obligatory":
            options = []
            shops = db.get_data("shops", {"obligatory": False}, fetch_all=True,
                                attribute="shop_id, name")
            if shops == []:
                await ctx.send("Es gibt keine Shops, welche freiwillig sind.", ephemeral=True, delete_after=5)
                return
            for shop_id, name in shops:
                options.append(i.StringSelectOption(
                    label=shop_id,
                    description=name,
                    value=shop_id
                ))
            menus = []
            for j in range(0, len(options) // 25 + 1):
                menus.append(
                    i.StringSelectMenu(
                        custom_id=f"shop_obligatory_id_select_{j}",
                        placeholder="Wähle die Shops aus die du freiwillig machen möchtest.",
                        *options[j*25:(j+1)*25],
                        min_values=1,
                        max_values=len(options[j*25:(j+1)*25])
                    )
                )
            for menu in menus:
                await ctx.send(components=menu, ephemeral=True, delete_after=25, silent=True)
        elif aktion == "voluntary":
            options = []
            shops = db.get_data("shops", {"obligatory": True}, fetch_all=True,
                                attribute="shop_id, name")
            if shops == []:
                await ctx.send("Es gibt keine Shops, mit Kaufplicht.", ephemeral=True, delete_after=5)
                return
            for shop_id, name in shops:
                options.append(i.StringSelectOption(
                    label=shop_id,
                    description=name,
                    value=shop_id
                ))
            menus = []
            for j in range(0, len(options) // 25 + 1):
                menus.append(
                    i.StringSelectMenu(
                        custom_id=f"shop_voluntary_id_select_{j}",
                        placeholder="Wähle die Shops aus die du freiwillig machen möchtest.",
                        *options[j*25:(j+1)*25],
                        min_values=1,
                        max_values=len(options[j*25:(j+1)*25])
                    )
                )
            for menu in menus:
                await ctx.send(components=menu, ephemeral=True, delete_after=25, silent=True)

    @ i.component_callback("shop_approve_id_select")
    async def shop_approve_id_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        for shop_id in ctx.values:
            shop = Shop(shop_id, self.client, ctx.channel)
            await shop.approve()
        await ctx.send("Shop(s) genehmigt.", ephemeral=True, delete_after=5)

    @ i.component_callback("shop_approve_id_select_0")
    async def shop_approve_id_select_0(self, ctx: i.ComponentContext):
        await self.shop_approve_id_select(ctx)

    @ i.component_callback("shop_approve_id_select_1")
    async def shop_approve_id_select_1(self, ctx: i.ComponentContext):
        await self.shop_approve_id_select(ctx)

    @ i.component_callback("shop_approve_id_select_2")
    async def shop_approve_id_select_2(self, ctx: i.ComponentContext):
        await self.shop_approve_id_select(ctx)

    @ i.component_callback("shop_deny_id_select")
    async def shop_deny_id_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        for shop_id in ctx.values:
            shop = Shop(shop_id, self.client, ctx.channel)
            await shop.deny()
        await ctx.send("Shop(s) abgelehnt.", ephemeral=True, delete_after=5)

    @ i.component_callback("shop_deny_id_select_0")
    async def shop_deny_id_select_0(self, ctx: i.ComponentContext):
        await self.shop_deny_id_select(ctx)

    @ i.component_callback("shop_deny_id_select_1")
    async def shop_deny_id_select_1(self, ctx: i.ComponentContext):
        await self.shop_deny_id_select(ctx)

    @ i.component_callback("shop_deny_id_select_2")
    async def shop_deny_id_select_2(self, ctx: i.ComponentContext):
        await self.shop_deny_id_select(ctx)

    @i.component_callback("admin_shop_owner_select")
    async def shop_owner_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        owners = []
        for user in ctx.values:
            owners.append(int(user.id))
        shop = self.transfer_data[int(ctx.author.id)]
        shop.owners = owners
        self.transfer_data[int(ctx.author.id)] = shop
        options = []
        for category in self.shop_categories:
            options.append(i.StringSelectOption(
                label=category,
                value=category
            ))
        category_select = i.StringSelectMenu(
            custom_id="admin_shop_category_select",
            placeholder="Wähle die Kategorie des Shops aus.",
            *options
        )
        await ctx.send(components=[category_select], ephemeral=True, delete_after=30)

    @i.component_callback("admin_shop_category_select")
    async def shop_category_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        shop: Shop = self.transfer_data[int(ctx.author.id)]
        shop.category = ctx.values[0]
        await shop.create()
        await ctx.send("Shop erstellt.", ephemeral=True, delete_after=5)

    @i.modal_callback("admin_shop_create")
    async def admin_shop_create(self, ctx: i.ModalContext, name: str, offer: str,
                                location: str):
        identifier = str(randint(1000, 9999))
        identifiers = self.get_shop_identifiers()
        while identifier in identifiers:
            identifier = str(randint(1000, 9999))
        self.transfer_data[int(ctx.author.id)] = Shop(
            identifier,
            self.client,
            ctx.channel,
            name=name,
            offer=offer,
            location=location,
            approved=True,
            skip_setup=True
        )
        user_select = i.UserSelectMenu(
            custom_id="admin_shop_owner_select",
            placeholder="Wähle die Besitzer des Shops aus.",
            min_values=1,
            max_values=25
        )
        await ctx.send(components=[user_select], ephemeral=True, delete_after=30)

    @i.component_callback("admin_shop_edit_id_select")
    async def shop_edit_id_select(self, ctx: i.ComponentContext):
        self.transfer_data[int(ctx.author.id)] = ctx.values[0]
        shop = Shop(ctx.values[0], self.client, ctx.channel)
        components = [
            i.InputText(
                label="Name",
                placeholder="Name",
                custom_id="name",
                style=i.TextStyles.SHORT,
                required=True,
                value=shop.name
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
        shop_edit_modal = i.Modal(
            title="Shop bearbeiten",
            custom_id="admin_shop_edit",
            *components
        )
        await ctx.send_modal(shop_edit_modal)

    @ i.component_callback("admin_shop_edit_id_select_0")
    async def shop_edit_id_select_0(self, ctx: i.ComponentContext):
        await self.shop_edit_id_select(ctx)

    @ i.component_callback("admin_shop_edit_id_select_1")
    async def shop_edit_id_select_1(self, ctx: i.ComponentContext):
        await self.shop_edit_id_select(ctx)

    @ i.component_callback("admin_shop_edit_id_select_2")
    async def shop_edit_id_select_2(self, ctx: i.ComponentContext):
        await self.shop_edit_id_select(ctx)

    @i.modal_callback("admin_shop_edit")
    async def admin_shop_edit(self, ctx: i.ModalContext, name: str, offer: str,
                              location: str):
        shop = Shop(self.transfer_data[int(
            ctx.author.id)], self.client, ctx.channel)
        shop.name = name
        shop.offer = offer
        shop.location = location
        await shop.update()
        await ctx.send("Shop bearbeitet.", ephemeral=True, delete_after=10)

    @i.component_callback("admin_shop_owner_select_shop")
    async def admin_shop_owner_select_shop(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        self.transfer_data[int(ctx.author.id)] = ctx.values[0]
        user_select = i.UserSelectMenu(
            custom_id="admin_shop_change_owner_select",
            placeholder="Wähle die Besitzer des Shops aus.",
            min_values=1,
            max_values=25
        )
        await ctx.send(components=[user_select], ephemeral=True, delete_after=20)

    @i.component_callback("admin_shop_owner_select_shop_0")
    async def admin_shop_owner_select_shop_0(self, ctx: i.ComponentContext):
        await self.admin_shop_owner_select_shop(ctx)

    @i.component_callback("admin_shop_owner_select_shop_1")
    async def admin_shop_owner_select_shop_1(self, ctx: i.ComponentContext):
        await self.admin_shop_owner_select_shop(ctx)

    @i.component_callback("admin_shop_owner_select_shop_2")
    async def admin_shop_owner_select_shop_2(self, ctx: i.ComponentContext):
        await self.admin_shop_owner_select_shop(ctx)

    @i.component_callback("admin_shop_change_owner_select")
    async def admin_shop_owner_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        shop = Shop(self.transfer_data[int(
            ctx.author.id)], self.client, ctx.channel)
        owners = []
        for user in ctx.values:
            owners.append(int(user.id))
        shop.set_owners(owners)
        await shop.update()
        await ctx.send("Besitzer geändert.", ephemeral=True, delete_after=5)

    @i.component_callback("shop_obligatory_id_select")
    async def shop_obligatory_id_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        for shop_id in ctx.values:
            shop = Shop(shop_id, self.client, ctx.channel)
            shop.obligatory = True
            await shop.update()
        await ctx.send("Die Shops haben nun eine Kaufplicht.", ephemeral=True, delete_after=5)

    @i.component_callback("shop_obligatory_id_select_0")
    async def shop_obligatory_id_select_0(self, ctx: i.ComponentContext):
        await self.shop_obligatory_id_select(ctx)

    @i.component_callback("shop_obligatory_id_select_1")
    async def shop_obligatory_id_select_1(self, ctx: i.ComponentContext):
        await self.shop_obligatory_id_select(ctx)

    @i.component_callback("shop_obligatory_id_select_2")
    async def shop_obligatory_id_select_2(self, ctx: i.ComponentContext):
        await self.shop_obligatory_id_select(ctx)

    @i.component_callback("shop_voluntary_id_select")
    async def shop_voluntary_id_select(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        for shop_id in ctx.values:
            shop = Shop(shop_id, self.client, ctx.channel)
            shop.obligatory = False
            await shop.update()
        await ctx.send("Die Shops sind nun freiwillig.", ephemeral=True, delete_after=5)

    @i.component_callback("shop_voluntary_id_select_0")
    async def shop_voluntary_id_select_0(self, ctx: i.ComponentContext):
        await self.shop_voluntary_id_select(ctx)

    @i.component_callback("shop_voluntary_id_select_1")
    async def shop_voluntary_id_select_1(self, ctx: i.ComponentContext):
        await self.shop_voluntary_id_select(ctx)

    @i.component_callback("shop_voluntary_id_select_2")
    async def shop_voluntary_id_select_2(self, ctx: i.ComponentContext):
        await self.shop_voluntary_id_select(ctx)

    @admin_base.subcommand(
        sub_cmd_name="config",
        sub_cmd_description="Config Command",
        options=[
            i.SlashCommandOption(
                name="aktion",
                description="Was soll gemacht werden?",
                required=True,
                type=i.OptionType.STRING,
                choices=[
                    i.SlashCommandChoice(name="bearbeiten", value="edit")
                ]
            )
        ]
    )
    async def admin_config(self, ctx: i.SlashContext, aktion: str) -> None:
        if aktion == "edit":
            with open('config.ini', 'r') as config_file:
                config_text = config_file.read()
            components = [
                i.InputText(
                    label="Config",
                    placeholder="Config",
                    value=config_text,
                    custom_id="config",
                    style=i.TextStyles.PARAGRAPH,
                    required=True
                )
            ]
            config_edit_modal = i.Modal(
                title="Kategorie bearbeiten",
                custom_id="admin_config_edit",
                *components
            )
            await ctx.send_modal(config_edit_modal)

    @i.modal_callback("admin_config_edit")
    async def admin_config_edit(self, ctx: i.ModalContext, config: str):
        with open('config.ini', 'w') as config_file:
            config_file.write(config)
        self.refresh_config()
        self.reload_extensions()
        await ctx.send("Config bearbeitet.", ephemeral=True, delete_after=5)
