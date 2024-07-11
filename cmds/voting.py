import configparser as cp
import sqlite3 as sql
from random import randint
from time import time

import interactions as i

import classes.database as db
from classes.voting import Voting

scope_ids = []


class VotingCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client: i.Client = client
        self.transfer_data = {}
        self.transfer_data["descriptions"] = {}
        self.refresh_config()

    @staticmethod
    def refresh_config() -> None:
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            global scope_ids
            scope_ids = config.get('General', 'servers').split(',')

    @staticmethod
    def get_identifiers() -> list[int]:
        con = sql.connect("data.db")
        cur = con.cursor()
        cur.execute("SELECT voting_id FROM votings")
        return [int(ident[0]) for ident in cur.fetchall()]

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
            sentences = [
                "Ist Ketchup ein Smoothie?",
                "Ist ein Hotdog ein Sandwich?",
                "Wenn jeder denkt, das Leben sei unfair - ist es dann nicht wieder fair?",
                "Wenn du gerne Zeit verschwendest, ist diese Zeit wirklich verschwendet?",
                "Wenn du ein Buch über Faulheit liest, bist du dann faul?",
                "Nutella mit oder ohne Butter?",
                "Ist Mayonesse auch ein Instrument?"
            ]
            components = [
                i.InputText(
                    style=i.TextStyles.PARAGRAPH,
                    label="Was willst du zur Abstimmung stellen?",
                    custom_id="text",
                    required=True,
                    placeholder=sentences[randint(0, len(sentences) - 1)],
                    value=self.transfer_data["descriptions"][int(ctx.author.id)] if int(
                        ctx.author.id) in self.transfer_data["descriptions"] else ""
                ),
                i.InputText(
                    style=i.TextStyles.SHORT,
                    label="Wie viel Entscheidungen gibt es? (2-10)",
                    custom_id="count",
                    required=True,
                    max_length=2
                ),
                i.InputText(
                    style=i.TextStyles.SHORT,
                    label="Abstimmungsdauer (1d, 15h, 3m, ...)",
                    custom_id="deadline",
                    required=True,
                    max_length=5
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
            await ctx.send("Wähle eine Abstimmung aus, die du löschen möchtest.", components=delete_selectmenu,
                           ephemeral=True, delete_after=90)
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
            await ctx.send("Wähle eine Abstimmung aus, die du bearbeiten möchtest.", components=edit_selectmenu,
                           ephemeral=True, delete_after=90)
        elif aktion == "close":
            options = []
            if db.get_data("votings", {"user_id": int(ctx.author.id)}, fetch_all=True) == []:
                await ctx.send("Es existieren keine Abstimmungen!", ephemeral=True,
                               delete_after=5)
                return
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
            await ctx.send("Wähle eine Abstimmung aus, die du beenden möchtest.", components=close_menu,
                           ephemeral=True, delete_after=90)

    @i.modal_callback("mod_create_voting")
    async def create_voting_response(self, ctx: i.ModalContext, text: str, count: str, deadline: str):
        self.transfer_data["descriptions"][int(ctx.author.id)] = text
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
        voting = Voting(identifier, self.client,
                        owner=ctx.author.id,
                        deadline=end_time,
                        description=text,
                        wait_time=deadline_in_seconds,
                        create_time=time(),
                        time_type=time_type,
                        count=count,
                        skip_setup=True
                        )
        await voting.create()
        await ctx.send("Die Abstimmung wurde entgegen genommen.", ephemeral=True,
                       delete_after=5)

    @i.component_callback("edit_voting_menu")
    async def edit_voting_response(self, ctx: i.ComponentContext):
        id = ctx.values[0]
        self.transfer_data[int(ctx.author.id)] = id
        voting = Voting(id, self.client)
        edit_modal = i.Modal(
            i.InputText(
                style=i.TextStyles.PARAGRAPH,
                label="Was willst du zur Abstimmung stellen?",
                custom_id="text",
                required=True,
                value=voting.description
            ),
            title="Abstimmung bearbeiten",
            custom_id="mod_edit_voting"
        )
        await ctx.send_modal(edit_modal)

    @i.modal_callback("mod_edit_voting")
    async def edit_voting(self, ctx: i.ModalContext, text: str):
        await ctx.defer(ephemeral=True)
        id = self.transfer_data[int(ctx.author.id)]
        voting = Voting(id, self.client)
        voting.description = text
        await voting.update()
        await ctx.send("Die Abstimmung wurde bearbeitet.", ephemeral=True,
                       delete_after=5)

    @i.component_callback("delete_voting_menu")
    async def delete_voting(self, ctx: i.ComponentContext):
        id = ctx.values[0]
        voting = Voting(id, self.client)
        await voting.delete()
        await ctx.send("Die Abstimmung wurde gelöscht.", ephemeral=True,
                       delete_after=5)

    @i.component_callback("close_voting_menu")
    async def close_voting(self, ctx: i.ComponentContext):
        await ctx.defer(ephemeral=True)
        for id in ctx.values:
            voting = Voting(id, self.client)
            await voting.close()
        await ctx.edit(content="Die Abstimmungen wurden beendet.", components=[])
