import configparser as cp
import json
from os import makedirs, path
from time import strftime, time, localtime
from random import randint

import interactions as dc

scope_ids = []


class VotingCommand(dc.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.data_folder_path = 'data/voting/'
        self.data_file_path = self.data_folder_path + 'voting.json'
        self.refresh_config()
        self.load_data()

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
        try:
            with open(self.data_file_path, 'r') as data_file:
                self.data = json.load(data_file)
        except json.decoder.JSONDecodeError:
            self.setup_data()
        except FileNotFoundError:
            self.setup_data()

    def setup_data(self):
        if not path.exists(self.data_folder_path):
            makedirs(self.data_folder_path)
        if not path.exists(self.data_file_path):
            open(self.data_file_path, 'a').close()
        with open("data.json", "w+") as data_file:
            # Do it so the main file knows where the votings are stored
            try:
                transfer_data = json.load(data_file)
            except json.decoder.JSONDecodeError:
                transfer_data = {}
            transfer_data["voting"] = {
                "data_file": self.data_file_path,
            }
            json.dump(transfer_data, data_file, indent=4)
        self.data = {
            "votings": {}
        }
        self.save_data()

    @dc.extension_command(
        name="abstimmung",
        description="Der Befehl für Abstimmungen.",
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
                    ),
                    dc.Choice(
                        name="beenden",
                        value="close"
                    )
                ]
            ),
            dc.Option(
                name="id",
                description="Die ID der Abstimmung.",
                type=dc.OptionType.INTEGER,
                required=False
            )
        ]
    )
    async def votings(self, ctx: dc.CommandContext, aktion: str, id: int = None):
        # TODO Get rid of the id parameter and use a selectmenu instead
        if aktion == "create":
            create_voting_modal = dc.Modal(
                title="Abstimmung erstellen",
                custom_id="mod_create_voting",
                components=[
                    dc.TextInput(
                        style=dc.TextStyleType.PARAGRAPH,
                        label="Welch Volksentscheid wollt ihr verkünden?",
                        custom_id="create_voting_text",
                        required=True,
                        placeholder="Liebe Mitbürger..."
                    ),
                    dc.TextInput(
                        style=dc.TextStyleType.SHORT,
                        label="Wie viel Entscheidungen habt ihr zu bieten?",
                        custom_id="create_voting_count",
                        required=True,
                        max_length=2
                    ),
                    dc.TextInput(
                        style=dc.TextStyleType.SHORT,
                        label="Wie lange läuft die Abstimmung?",
                        custom_id="create_voting_deadline",
                        required=True,
                        max_length=3
                    )
                ]
            )
            await ctx.popup(create_voting_modal)
        elif aktion == "delete":
            delete_modal = dc.Modal(
                title="Abstimmung löschen",
                custom_id="mod_delete_voting",
                components=[
                    dc.TextInput(
                        style=dc.TextStyleType.SHORT,
                        label="ID der Abstimmung",
                        custom_id="delete_voting_id",
                        required=True,
                        min_length=4,
                        max_length=4,
                        value=str(id) if id else ""
                    )
                ]
            )
            await ctx.popup(delete_modal)
        elif aktion == "edit":
            edit_voting_modal = dc.Modal(
                title="Abstimmung bearbeiten",
                custom_id="mod_edit_voting",
                components=[
                    dc.TextInput(
                        style=dc.TextStyleType.SHORT,
                        label="ID der Abstimmmung",
                        custom_id="edit_voting_id",
                        required=True,
                        min_length=4,
                        max_length=4,
                        value=str(id) if id else ""
                    ),
                    dc.TextInput(
                        style=dc.TextStyleType.PARAGRAPH,
                        label="Abstimmungstext",
                        custom_id="edit_voting_text",
                        required=True
                    )
                ]
            )
            await ctx.popup(edit_voting_modal)
        elif aktion == "close":
            close_modal = dc.Modal(
                title="Abstimmung beenden",
                custom_id="mod_close_voting",
                components=[
                    dc.TextInput(
                        style=dc.TextStyleType.SHORT,
                        label="ID der Abstimmung",
                        custom_id="close_voting_id",
                        required=True,
                        min_length=4,
                        max_length=4,
                        value=str(id) if id else ""
                    )
                ]
            )
            await ctx.popup(close_modal)

    @dc.extension_modal("mod_create_voting")
    async def create_voting_response(self, ctx: dc.CommandContext, text: str, count: str, deadline: str):
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
        identifier = randint(1000, 9999)
        while identifier in self.data["votings"]:
            identifier = randint(1000, 9999)

        self.data["votings"][str(identifier)] = {
            "user_id": str(ctx.author.id),
            "text": text
        }

        count = 2 if int(count) < 2 else count
        end_time = time() + float(deadline) * time_in_seconds
        self.data["votings"][str(identifier)]["deadline"] = end_time
        wait_time = end_time - time()
        # TODO Lesezeichen
        self.client._loop.call_later(wait_time, run_delete, True)
        end_time = strftime("%d.%m.") + "- " + \
            strftime("%d.%m. %H:%M", localtime(int(end_time)))

        server: dc.Guild = await ctx.get_guild()
        voting_role_to_ping: dc.Role = await server.get_role(voting_role_to_ping_id)
        voting_embed = dc.Embed(
            title="Liebe Mitbürger",
            description=f"\n{text}",
            color=0xdaa520,
            author=dc.EmbedAuthor(
                name=f"{ctx.user.username}, {end_time} ({deadline} {time_type})"),
            footer=dc.EmbedFooter(text=identifier)
        )
        channel = await ctx.get_channel()
        sent_message = await channel.send(content=voting_role_to_ping.mention, embeds=voting_embed)
        emote_index = 0
        while int(count) > emote_index:
            await sent_message.create_reaction(emote_chars[emote_index])
            emote_index += 1
            sleep(0.5)
        data["votings"][str(identifier)]["message_id"] = str(sent_message.id)
        json_dump(data)
        await ctx.send("Die Abstimmung wurde entgegen genommen.", ephemeral=True)

    @bot.modal("mod_delete_voting")
    async def delete_voting_response(ctx: dc.CommandContext, id: str):
        try:
            int(id)
        except ValueError:
            await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
            return
        except BaseException as e:
            await ctx.send(
                f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
            return
        if id not in data["votings"]:
            await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
            return
        if not data["votings"][id]["user_id"] == str(ctx.author.id) and not user_is_privileged(ctx.author.roles):
            await ctx.send("Du bist nicht berechtigt diese Abstimmung zu löschen!",
                           ephemeral=True)
            return
        votings_channel: dc.Channel = await ctx.get_channel()
        voting_message: dc.Message = await votings_channel.get_message(data["votings"][id]["message_id"])
        await voting_message.delete(reason=f"[Manuell] {ctx.user.username}")
        del data["votings"][id]
        json_dump(data)
        await ctx.send("Die Abstimmung wurde gelöscht.", ephemeral=True)

    @bot.modal("mod_edit_voting")
    async def edit_voting_response(ctx: dc.CommandContext, id: str, text: str):
        try:
            int(id)
        except ValueError:
            await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
            return
        except BaseException as e:
            await ctx.send(
                f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
            return
        if id not in data["votings"]:
            await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
            return
        if not data["votings"][id]["user_id"] == str(ctx.author.id):
            await ctx.send("Du bist nicht berechtigt diese Abstimmung zu bearbeiten!",
                           ephemeral=True)
            return
        voting_channel: dc.Channel = await ctx.get_channel()
        voting_message: dc.Message = await voting_channel.get_message(data["votings"][id]["message_id"])
        message_embed: dc.Embed = voting_message.embeds[0]
        text = message_embed.description if type(
            text) is None or text == " " else text
        if "bearbeitet" not in text:
            text = text + "\n*bearbeitet*"
        message_embed.description = text
        server: dc.Guild = await ctx.get_guild()
        voting_role_to_ping: dc.Role = await server.get_role(voting_role_to_ping_id)
        await voting_message.edit(content=voting_role_to_ping.mention, embeds=message_embed)
        await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)

    @bot.modal("mod_close_voting")
    async def close_voting_response(ctx: dc.CommandContext, id: str):
        try:
            int(id)
        except ValueError:
            await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
            return
        except BaseException as e:
            await ctx.send(
                f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
            return
        if id not in data["votings"]:
            await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
            return
        if not data["votings"][id]["user_id"] == str(ctx.author.id) and not user_is_privileged(ctx.author.roles):
            await ctx.send("Du bist nicht berechtigt diese Abstimmung zu beenden!",
                           ephemeral=True)
            return
        votings_channel: dc.Channel = await ctx.get_channel()
        voting_message: dc.Message = await votings_channel.get_message(data["votings"][id]["message_id"])
        message_embed: dc.Embed = evaluate_voting(voting_message)
        current_time_formatted = strftime("%d.%m. %H:%M")
        message_embed.description = "**Diese Abstimmung wurde vorzeitig beendet!**\n" \
            + f"{ctx.user.username}, {current_time_formatted}" \
            + "\n\n" + message_embed.description
        await voting_message.edit(embeds=message_embed)
        del data["votings"][id]
        json_dump(data)
        await ctx.send("Die Abstimmung wurde beendet.", ephemeral=True)
