import configparser as cp
import sqlite3 as sql
from random import randint
from time import localtime, strftime, time

import interactions as i

import classes.database as db

scope_ids = []


class OfferCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.refresh_config()

    def refresh_config(self):
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            global scope_ids
            scope_ids = config.get('General', 'servers').split(',')
            self.role_to_ping_id = config.getint(
                'Offer', 'ping_role')

    @staticmethod
    def get_identifiers() -> list[str]:
        con = sql.connect("data.db")
        cur = con.cursor()
        cur.execute("SELECT offer_id FROM offers")
        return [str(ident[0]) for ident in cur.fetchall()]

    @i.slash_command(
        name="angebot",
        description="Der Befehl für Angebote.",
        scopes=scope_ids,
        options=[
            i.SlashCommandOption(
                name="aktion",
                description="Das, was du tun willst.",
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
            if db.get_data("users", {"user_id": str(ctx.author.id)}) is None:
                db.save_data("users", "user_id, offers_count, shop_count",
                             (int(ctx.author.id), 0, 0))

            offer_count = db.get_data(
                "users", {"user_id": int(ctx.author.id)}, attribute="offers_count")[0]
            if offer_count is None:
                offer_count = 0
                db.save_data("users", "user_id, offers_count, shop_count",
                             (int(ctx.author.id), 0, 0))
            elif int(offer_count) >= 3:
                await ctx.send("Du hast bereits 3 Angebote erstellt.", ephemeral=True)
                return

            components = [
                i.InputText(
                    style=i.TextStyles.SHORT,
                    label="Titel",
                    custom_id="title",
                    required=True
                ),
                i.InputText(
                    style=i.TextStyles.SHORT,
                    label="Preis",
                    custom_id="price",
                    value="VB"
                ),
                i.InputText(
                    style=i.TextStyles.PARAGRAPH,
                    label="Was bietest du an?",
                    custom_id="text",
                    required=True
                ),
                i.InputText(
                    style=i.TextStyles.SHORT,
                    label="Wie lange läuft das Angebot? (1-7)",
                    custom_id="deadline",
                    required=True,
                    max_length=1
                )
            ]
            create_modal = i.Modal(
                title="Angebot erstellen",
                custom_id="mod_create_offer",
                *components
            )
            await ctx.send_modal(create_modal)
        elif aktion == "delete":
            options = []
            for offer in db.get_data("offers", {"user_id": str(ctx.author.id)}, attribute="offer_id, title", fetch_all=True):
                options.append(
                    i.StringSelectOption(
                        label=offer[0],
                        value=offer[0],
                        description=offer[1]
                    )
                )
            if len(options) == 0:
                await ctx.send("Du hast keine Angebote, die du löschen kannst.", ephemeral=True)
                return
            delete_selectmenu = i.StringSelectMenu(
                custom_id="delete_offer_menu",
                placeholder="Wähle ein Angebot aus",
                *options,
                min_values=1,
                max_values=len(options)
            )
            await ctx.send("Wähle die Angebote aus, die du löschen möchtest.", components=delete_selectmenu, ephemeral=True)
        elif aktion == "edit":
            options = []
            for offer in db.get_data("offers", {"user_id": str(ctx.author.id)}, attribute="offer_id, title", fetch_all=True):
                options.append(
                    i.StringSelectOption(
                        label=offer[0],
                        value=offer[0],
                        description=offer[1]
                    )
                )
            if len(options) == 0:
                await ctx.send("Es gibt keine Angebote, die du bearbeiten kannst.", ephemeral=True)
                return
            edit_selectmenu = i.StringSelectMenu(
                custom_id="edit_offer_menu",
                placeholder="Wähle ein Angebot aus",
                *options,
                min_values=1,
                max_values=1
            )
            await ctx.send("Wähle das Angebot aus, das du bearbeiten möchtest.", components=edit_selectmenu, ephemeral=True)

    @i.modal_callback("mod_create_offer")
    async def create_offer_respone(self, ctx: i.SlashContext, title: str, price: str, text: str, deadline: str):
        identifier_list = self.get_identifiers()
        identifier = randint(1000, 9999)
        while identifier in identifier_list:
            identifier = randint(1000, 9999)

        if int(deadline) < 1:
            deadline = 1
        elif int(deadline) > 7:
            deadline = 7
        # The deadline is: current_time_seconds_epoch + x * seconds_of_one_day
        numeric_end_time = time() + int(deadline) * 86400
        end_time = strftime("%d.%m.") + "- " + \
            strftime("%d.%m.", localtime(numeric_end_time))
        app_embed = i.Embed(
            title=title,
            description=f"\n{text}\n\n**Preis:** {price}",
            color=0xdaa520,
            author=i.EmbedAuthor(
                name=f"{ctx.user.username}, {end_time} ({deadline} Tage)"),
            footer=i.EmbedFooter(text=str(identifier))
        )
        channel = ctx.channel
        server: i.Guild = ctx.guild
        role_to_ping: i.Role = server.get_role(
            self.role_to_ping_id)
        sent_message = await channel.send(content=role_to_ping.mention, embeds=app_embed)

        db.save_data("offers", "offer_id, title, user_id, price, description, deadline, message_id",
                     (identifier, title, int(ctx.author.id), price, text, numeric_end_time, int(sent_message.id)))
        offer_count = int(db.get_data(
            "users", {"user_id": int(ctx.author.id)}, attribute="offers_count")[0])
        db.update_data("users", "offers_count", offer_count +
                       1, {"user_id": int(ctx.author.id)})
        await ctx.send("Das Angebot wurde entgegen genommen.", ephemeral=True)

    @i.component_callback("delete_offer_menu")
    async def delete_offer_response(self, ctx: i.SlashContext):
        await ctx.defer(ephemeral=True)
        offer_channel: i.GuildText = ctx.channel
        for id in ctx.values:
            message_id = db.get_data(
                "offers", {"offer_id": id}, attribute="message_id")[0]
            offer_message: i.Message = await offer_channel.fetch_message(message_id)
            await offer_message.delete()
            db.delete_data("offers", {"offer_id": id})
            offer_count = int(db.get_data(
                "users", {"user_id": int(ctx.author.id)}, attribute="offers_count")[0])
            db.update_data("users", "offers_count", offer_count - 1,
                           {"user_id": int(ctx.author.id)})
        await ctx.send("Die Angebote wurden gelöscht.", ephemeral=True)

    @i.component_callback("edit_offer_menu")
    async def edit_offer_response(self, ctx: i.ComponentContext):
        title, text = db.get_data(
            "offers", {"offer_id": ctx.values[0]}, attribute="title, description", fetch_all=True)[0]
        components = [
            i.InputText(
                style=i.TextStyles.SHORT,
                label="Titel",
                custom_id="title",
                required=True,
                value=title
            ),
            i.InputText(
                style=i.TextStyles.PARAGRAPH,
                label="Text",
                custom_id="text",
                required=True,
                value=text.replace("\\n", "\n")
            ),
            i.InputText(
                style=i.TextStyles.SHORT,
                label="ID",
                custom_id="id",
                required=True,
                max_length=4,
                value=ctx.values[0]
            )
        ]
        edit_modal = i.Modal(
            title="Angebot bearbeiten",
            custom_id="mod_edit_offer",
            *components
        )
        await ctx.send_modal(edit_modal)

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

        if id not in self.get_identifiers():
            await ctx.send("Diese ID existiert nicht!", ephemeral=True)
            return
        offer_owner_id = db.get_data(
            "offers", {"offer_id": id}, attribute="user_id")[0]
        if str(offer_owner_id) != str(ctx.author.id):
            await ctx.send("Du bist nicht berechtigt dieses Angebot zu bearbeiten!",
                           ephemeral=True)
            return
        message_id, price = db.get_data(
            "offers", {"offer_id": id}, attribute="message_id, price", fetch_all=True)[0]
        offer_channel: i.GuildText = ctx.channel
        offer_message: i.Message = await offer_channel.fetch_message(message_id)
        message_embed: i.Embed = offer_message.embeds[0]
        edited_text = f"{text}\n\n**Preis:** {price}\n*bearbeitet *"
        message_embed.title = title
        message_embed.description = edited_text
        await offer_message.edit(embeds=message_embed)
        db.update_data("offers", "title", title, {"offer_id": id})
        db.update_data("offers", "description", text, {"offer_id": id})
        await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)
