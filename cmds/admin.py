import configparser as cp
import database as db

import interactions as i

scope_ids = []


class AdminCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.refresh_config()

    def refresh_config(self) -> None:
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            global scope_ids
            scope_ids = config.get('IDs', 'server').split(',')

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
                ]
            )
        ]
    )
    async def admin_shop(self, ctx: i.SlashContext, aktion: str) -> None:
        await ctx.defer(ephemeral=True)
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
            shop_approve_select_menu = i.StringSelectMenu(
                custom_id="shop_approve_id_select",
                placeholder="Wähle die Shops aus die du genehmigen möchtest.",
                min_values=1,
                max_values=len(options),
                *options
            )
            await ctx.send(components=[shop_approve_select_menu], ephemeral=True)
        elif aktion == "deny":
            options = []
            shops = db.get_data("shops", {"approved": True}, fetch_all=True,
                                attribute="shop_id, name")
            if shops == []:
                await ctx.send("Es gibt keine genehmigten Shops.", ephemeral=True)
                return
            for shop_id, name in shops:
                options.append(i.StringSelectOption(
                    label=shop_id,
                    description=name,
                    value=shop_id
                ))
            shop_deny_select_menu = i.StringSelectMenu(
                custom_id="shop_deny_id_select",
                placeholder="Wähle die Shops aus die du ablehnen möchtest.",
                min_values=1,
                max_values=len(options),
                *options
            )
            await ctx.send(components=[shop_deny_select_menu], ephemeral=True)
