import configparser as cp
from random import randint
from time import localtime, sleep, strftime, time
import database as db
import sqlite3 as sql

import interactions as i

scope_ids = []


class VotingCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client: i.Client = client
        self.emote_chars = ["\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9", "\U0001F1EA",
                            "\U0001F1EB", "\U0001F1EC", "\U0001F1ED", "\U0001F1EE", "\U0001F1EF"]
        self.transfer_data = {}
        self.refresh_config()

    def refresh_config(self) -> None:
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            global scope_ids
            scope_ids = config.get('IDs', 'server').split(',')
            self.privileged_roles_ids = [int(id) for id in config.get(
                'IDs', 'privileged_roles').split(',')]
            self.voting_role_to_ping_id = config.getint(
                'IDs', 'voting_role_to_ping')

    @staticmethod
    def get_identifiers() -> list[int]:
        con = sql.connect("data.db")
        cur = con.cursor()
        cur.execute("SELECT voting_id FROM votings")
        return [int(ident[0]) for ident in cur.fetchall()]

    def user_is_privileged(self, roles: list[int]) -> bool:
        return any(role in self.privileged_roles_ids for role in roles)

    @staticmethod
    def evaluate_voting(message: i.Message) -> str:
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
        message_embed: i.Embed = message.embeds[0]
        message_embed.description = message_embed.description + \
            f"\n\n**Ergebnis:** {winner}"
        return message_embed

    @i.slash_command(
        name="abstimmung",
        description="Der Befehl für Abstimmungen.",
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
                    ),
                    i.SlashCommandChoice(
                        name="beenden",
                        value="close"
                    )
                ]
            )
        ]
    )
    async def votings(self, ctx: i.SlashContext, aktion: str):
        if aktion == "create":
            components = [
                i.InputText(
                    style=i.TextStyles.PARAGRAPH,
                    label="Welch Volksentscheid wollt ihr verkünden?",
                    custom_id="text",
                    required=True,
                    placeholder="Liebe Mitbürger..."
                ),
                i.InputText(
                    style=i.TextStyles.SHORT,
                    label="Wie viel Entscheidungen habt ihr zu bieten?",
                    custom_id="count",
                    required=True,
                    max_length=2
                ),
                i.InputText(
                    style=i.TextStyles.SHORT,
                    label="Wie lange läuft die Abstimmung?",
                    custom_id="deadline",
                    required=True,
                    max_length=3
                )
            ]
            create_voting_modal = i.Modal(
                title="Abstimmung erstellen",
                custom_id="mod_create_voting",
                *components
            )
            await ctx.send_modal(create_voting_modal)
        elif aktion == "delete":
            options = []
            if db.get_data("votings", {"user_id": int(ctx.author.id)}, fetch_all=True) == []:
                await ctx.send("Es existieren keine Abstimmungen!")
                return
            if self.user_is_privileged(ctx.author.roles):
                votings: list[tuple] = db.get_data(
                    "votings", attribute="voting_id", fetch_all=True)
            else:
                votings: list[tuple] = db.get_data(
                    "votings", {"user_id": int(ctx.author.id)}, attribute="voting_id", fetch_all=True)
            for voting_tuple in votings:
                options.append(
                    i.StringSelectOption(
                        label=voting_tuple[0],
                        value=voting_tuple[0]
                    )
                )
            delete_selectmenu = i.StringSelectMenu(
                custom_id="delete_voting_menu",
                placeholder="Wähle eine Abstimmung aus",
                *options
            )
            await ctx.send("Wähle eine Abstimmung aus, die du löschen möchtest.", components=delete_selectmenu, ephemeral=True)
        elif aktion == "edit":
            votings = db.get_data(
                "votings", {"user_id": int(ctx.author.id)}, attribute="voting_id", fetch_all=True)
            if votings == []:
                await ctx.send("Es existieren keine Abstimmungen!")
                return
            options = []
            for voting_tuple in votings:
                options.append(
                    i.StringSelectOption(
                        label=voting_tuple[0],
                        value=voting_tuple[0]
                    )
                )
            edit_selectmenu = i.StringSelectMenu(
                custom_id="edit_voting_menu",
                placeholder="Wähle eine Abstimmung aus",
                *options
            )
            await ctx.send("Wähle eine Abstimmung aus, die du bearbeiten möchtest.", components=edit_selectmenu, ephemeral=True)
        elif aktion == "close":
            options = []
            if db.get_data("votings", {"user_id": int(ctx.author.id)}, fetch_all=True) == []:
                await ctx.send("Es existieren keine Abstimmungen!")
                return
            if self.user_is_privileged(ctx.author.roles):
                votings: list[tuple] = db.get_data(
                    "votings", attribute="voting_id", fetch_all=True)
            else:
                votings: list[tuple] = db.get_data(
                    "votings", {"user_id": int(ctx.author.id)}, attribute="voting_id", fetch_all=True)
            for voting_tuple in votings:
                options.append(
                    i.StringSelectOption(
                        label=voting_tuple[0],
                        value=voting_tuple[0]
                    )
                )
            close_menu = i.StringSelectMenu(
                custom_id="close_voting_menu",
                placeholder="Wähle eine Abstimmung aus",
                *options,
                max_values=len(options)
            )
            await ctx.send("Wähle eine Abstimmung aus, die du beenden möchtest.", components=close_menu, ephemeral=True)

    @i.modal_callback("mod_create_voting")
    async def create_voting_response(self, ctx: i.ModalContext, text: str, count: str, deadline: str):
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
        await ctx.defer(ephemeral=True)
        deadline_in_seconds = float(deadline) * time_in_seconds
        identifier = randint(1000, 9999)
        identifiers = self.get_identifiers()
        while identifier in identifiers:
            identifier = randint(1000, 9999)
        end_time = time() + deadline_in_seconds
        db.save_data("votings", "voting_id, user_id, description, create_time, wait_time, deadline",
                     (identifier, int(ctx.author.id), text, time(), deadline_in_seconds, end_time))

        formatted_end_time = strftime("%d.%m.") + "- " + \
            strftime("%d.%m. %H:%M", localtime(int(end_time)))

        server: i.Guild = ctx.guild
        voting_role_to_ping: i.Role = server.get_role(
            self.voting_role_to_ping_id)
        voting_embed = i.Embed(
            title="Liebe Mitbürger",
            description=f"\n{text}",
            color=0xdaa520,
            author=i.EmbedAuthor(
                name=f"{ctx.user.username}, {formatted_end_time} ({deadline} {time_type})"),
            footer=i.EmbedFooter(text=str(identifier))
        )
        channel = ctx.channel
        sent_message = await channel.send(content=voting_role_to_ping.mention, embeds=voting_embed)
        emote_index = 0
        count = 2 if int(count) < 2 else count
        while int(count) > emote_index:
            await sent_message.add_reaction(self.emote_chars[emote_index])
            emote_index += 1
            sleep(0.5)
        db.update_data("votings", "message_id", int(
            sent_message.id), {"voting_id": identifier})
        await ctx.send("Die Abstimmung wurde entgegen genommen.", ephemeral=True)

    @i.component_callback("edit_voting_menu")
    async def edit_voting_response(self, ctx: i.ComponentContext):
        id = ctx.values[0]
        self.transfer_data[int(ctx.author.id)] = id
        text: str = db.get_data(
            "votings", {"voting_id": id}, attribute="description")[0]
        text = text.replace("\\n", "\n")
        edit_modal = i.Modal(
            i.InputText(
                style=i.TextStyles.PARAGRAPH,
                label="Welch Volksentscheid wollt ihr verkünden?",
                custom_id="text",
                required=True,
                value=text
            ),
            title="Abstimmung bearbeiten",
            custom_id="mod_edit_voting"
        )
        await ctx.send_modal(edit_modal)

    @i.modal_callback("mod_edit_voting")
    async def edit_voting(self, ctx: i.ModalContext, text: str):
        await ctx.defer(ephemeral=True)
        id = self.transfer_data[int(ctx.author.id)]
        message_id = db.get_data(
            "votings", {"voting_id": id}, attribute="message_id")[0]
        voting_channel: i.GuildText = ctx.channel
        voting_message: i.Message = await voting_channel.fetch_message(message_id)
        message_embed: i.Embed = voting_message.embeds[0]
        if "bearbeitet" not in text:
            text = text + "\n*bearbeitet*"
        message_embed.description = text
        server: i.Guild = ctx.guild
        voting_role_to_ping: i.Role = await server.fetch_role(
            self.voting_role_to_ping_id)
        await voting_message.edit(content=voting_role_to_ping.mention, embeds=message_embed)
        db.update_data("votings", "description", text, {"voting_id": id})
        await ctx.send("Die Abstimmung wurde bearbeitet.", ephemeral=True)

    @i.component_callback("delete_voting_menu")
    async def delete_voting(self, ctx: i.ComponentContext):
        id = ctx.values[0]
        message_id = db.get_data(
            "votings", {"voting_id": id}, attribute="message_id")[0]
        votings_channel: i.GuildText = ctx.channel
        voting_message: i.Message = await votings_channel.fetch_message(message_id)
        await voting_message.delete()
        db.delete_data("votings", {"voting_id": id})
        await ctx.send("Die Abstimmung wurde gelöscht.", ephemeral=True)

    @i.component_callback("close_voting_menu")
    async def close_voting(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        votings_channel: i.GuildText = ctx.channel
        for id in ctx.values:
            message_id = db.get_data(
                "votings", {"voting_id": int(id)}, attribute="message_id")[0]
            voting_message: i.Message = await votings_channel.fetch_message(message_id)
            message_embed: i.Embed = self.evaluate_voting(voting_message)
            current_time_formatted = strftime("%d.%m. %H:%M")
            message_embed.description = "**Diese Abstimmung wurde vorzeitig beendet!**\n" \
                + f"{ctx.user.username}, {current_time_formatted}" \
                + "\n\n" + message_embed.description
            await voting_message.edit(embeds=message_embed)
            db.delete_data("votings", {"voting_id": int(id)})
        await ctx.edit(content="Die Abstimmungen wurden beendet.", components=[])
