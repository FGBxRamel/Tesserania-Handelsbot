import configparser as cp
import json
import sys
from os import makedirs, path
from random import randint
from time import localtime, sleep, strftime, time

import interactions as i

scope_ids = []


class VotingCommand(i.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.data_folder_path = 'data/voting/'
        self.data_file_path = self.data_folder_path + 'voting.json'
        self.emote_chars = ["\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9", "\U0001F1EA",
                            "\U0001F1EB", "\U0001F1EC", "\U0001F1ED", "\U0001F1EE", "\U0001F1EF"]
        self.data = {}
        self.refresh_config()
        self.setup_data()

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

    def save_data(self) -> None:
        with open(self.data_file_path, 'w+') as data_file:
            json.dump(self.data, data_file, indent=4)

    def load_data(self) -> None:
        with open(self.data_file_path, 'r') as data_file:
            self.data = json.load(data_file)

    def setup_data(self) -> None:
        def create_data_file():
            open(self.data_file_path, 'a').close()
            self.data = {}
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

        with open("data.json", "r") as data_file:
            try:
                transfer_data = json.load(data_file)
            except json.decoder.JSONDecodeError:
                data_file_content = data_file.read()
                print(
                    f"data.json could not be loaded! It probably is empty.\n{data_file_content}")
                sys.exit()
        with open("data.json", "w") as data_file:
            # Do it so the main file knows where the votings are stored
            transfer_data["voting"] = {
                "data_file": self.data_file_path,
            }
            json.dump(transfer_data, data_file, indent=4)

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
            i.Option(
                name="aktion",
                description="Das, was du tuen willst.",
                type=i.OptionType.STRING,
                required=True,
                choices=[
                    i.Choice(
                        name="erstellen",
                        value="create"
                    ),
                    i.Choice(
                        name="löschen",
                        value="delete"
                    ),
                    i.Choice(
                        name="bearbeiten",
                        value="edit"
                    ),
                    i.Choice(
                        name="beenden",
                        value="close"
                    )
                ]
            ),
            i.Option(
                name="id",
                description="Die ID des Shops, den du bearbeiten möchtest.",
                type=i.OptionType.INTEGER,
                required=False,
                max_value=9999
            )
        ]
    )
    async def votings(self, ctx: i.SlashContext, aktion: str, id: int = None):
        if aktion == "create":
            create_voting_modal = i.Modal(
                title="Abstimmung erstellen",
                custom_id="mod_create_voting",
                components=[
                    i.TextInput(
                        style=i.TextStyleType.PARAGRAPH,
                        label="Welch Volksentscheid wollt ihr verkünden?",
                        custom_id="create_voting_text",
                        required=True,
                        placeholder="Liebe Mitbürger..."
                    ),
                    i.TextInput(
                        style=i.TextStyleType.SHORT,
                        label="Wie viel Entscheidungen habt ihr zu bieten?",
                        custom_id="create_voting_count",
                        required=True,
                        max_length=2
                    ),
                    i.TextInput(
                        style=i.TextStyleType.SHORT,
                        label="Wie lange läuft die Abstimmung?",
                        custom_id="create_voting_deadline",
                        required=True,
                        max_length=3
                    )
                ]
            )
            await ctx.popup(create_voting_modal)
        elif aktion == "delete":
            voting_options = []
            for voting_id, voting_data in self.data.items():
                if voting_data["user_id"] == str(ctx.author.id):
                    voting_options.append(
                        i.SelectOption(
                            label=voting_id,
                            value=voting_id
                        )
                    )
            delete_selectmenu = i.SelectMenu(
                custom_id="delete_voting_menu",
                placeholder="Wähle eine Abstimmung aus",
                options=voting_options
            )
            await ctx.send("Wähle eine Abstimmung aus, die du löschen möchtest.", components=delete_selectmenu, ephemeral=True)
        elif aktion == "edit":
            edit_voting_modal = i.Modal(
                title="Abstimmung bearbeiten",
                custom_id="mod_edit_voting",
                components=[
                    i.TextInput(
                        style=i.TextStyleType.SHORT,
                        label="ID der Abstimmmung",
                        custom_id="edit_voting_id",
                        required=True,
                        min_length=4,
                        max_length=4,
                        value=str(id) if id else "0000"
                    ),
                    i.TextInput(
                        style=i.TextStyleType.PARAGRAPH,
                        label="Abstimmungstext",
                        custom_id="edit_voting_text",
                        required=True
                    )
                ]
            )
            await ctx.popup(edit_voting_modal)
        elif aktion == "close":
            close_options = []
            for voting_id, voting_data in self.data.items():
                if voting_data["user_id"] == str(ctx.author.id) or self.user_is_privileged(ctx.author.roles):
                    close_options.append(
                        i.SelectOption(
                            label=voting_id,
                            value=voting_id
                        )
                    )
            close_menu = i.SelectMenu(
                custom_id="close_voting_menu",
                placeholder="Wähle eine Abstimmung aus",
                options=close_options,
                max_values=len(close_options)
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
        self.load_data()
        while identifier in self.data:
            identifier = randint(1000, 9999)

        end_time = time() + deadline_in_seconds
        self.data[str(identifier)] = {
            "user_id": str(ctx.author.id),
            "text": text,
            "create_time": time(),
            "wait_time": deadline_in_seconds,
            "deadline": end_time
        }

        end_time = strftime("%d.%m.") + "- " + \
            strftime("%d.%m. %H:%M", localtime(int(end_time)))

        server: i.Guild = await ctx.get_guild()
        voting_role_to_ping: i.Role = await server.get_role(self.voting_role_to_ping_id)
        voting_embed = i.Embed(
            title="Liebe Mitbürger",
            description=f"\n{text}",
            color=0xdaa520,
            author=i.EmbedAuthor(
                name=f"{ctx.user.username}, {end_time} ({deadline} {time_type})"),
            footer=i.EmbedFooter(text=identifier)
        )
        channel = await ctx.get_channel()
        sent_message = await channel.send(content=voting_role_to_ping.mention, embeds=voting_embed)
        emote_index = 0
        count = 2 if int(count) < 2 else count
        while int(count) > emote_index:
            await sent_message.create_reaction(self.emote_chars[emote_index])
            emote_index += 1
            sleep(0.5)
        self.data[str(identifier)]["message_id"] = str(sent_message.id)
        self.save_data()
        await ctx.send("Die Abstimmung wurde entgegen genommen.", ephemeral=True)

    @i.modal_callback("mod_delete_voting")
    async def delete_voting_response(self, ctx: i.ModalContext, id: str):
        try:
            int(id)
        except ValueError:
            await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
            return
        except BaseException as e:
            await ctx.send(
                f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
            return
        self.load_data()
        if id not in self.data:
            await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
            return
        if not self.data[id]["user_id"] == str(ctx.author.id) and not self.user_is_privileged(ctx.author.roles):
            await ctx.send("Du bist nicht berechtigt diese Abstimmung zu löschen!",
                           ephemeral=True)
            return
        votings_channel: i.Channel = await ctx.get_channel()
        voting_message: i.Message = await votings_channel.get_message(self.data[id]["message_id"])
        await voting_message.delete(reason=f"[Manuell] {ctx.user.username}")
        del self.data[id]
        self.save_data()
        await ctx.send("Die Abstimmung wurde gelöscht.", ephemeral=True)

    @i.modal_callback("mod_edit_voting")
    async def edit_voting_response(self, ctx: i.ModalContext, id: str, text: str):
        try:
            int(id)
        except ValueError:
            await ctx.send("Die ID hat ein fehlerhaftes Format!", ephemeral=True)
            return
        except BaseException as e:
            await ctx.send(
                f"Oops, etwas ist schief gegangen! Fehler: {e}", ephemeral=True)
            return
        self.load_data()
        if id not in self.data:
            await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
            return
        if not self.data[id]["user_id"] == str(ctx.author.id):
            await ctx.send("Du bist nicht berechtigt diese Abstimmung zu bearbeiten!",
                           ephemeral=True)
            return
        voting_channel: i.Channel = await ctx.get_channel()
        voting_message: i.Message = await voting_channel.get_message(self.data[id]["message_id"])
        message_embed: i.Embed = voting_message.embeds[0]
        text = message_embed.description if type(
            text) is None or text == " " else text
        if "bearbeitet" not in text:
            text = text + "\n*bearbeitet*"
        message_embed.description = text
        server: i.Guild = await ctx.get_guild()
        voting_role_to_ping: i.Role = await server.get_role(self.voting_role_to_ping_id)
        await voting_message.edit(content=voting_role_to_ping.mention, embeds=message_embed)
        await ctx.send("Das Angebot wurde bearbeitet.", ephemeral=True)

    @i.component_callback("delete_voting_menu")
    async def delete_voting(self, ctx: i.ComponentContext, ids: list):
        id = ids[0]
        self.load_data()
        if id not in self.data:
            await ctx.send("Diese ID existiert nicht oder die Abstimmung ist vorbei!", ephemeral=True)
            return
        if not self.data[id]["user_id"] == str(ctx.author.id) and not self.user_is_privileged(ctx.author.roles):
            await ctx.send("Du bist nicht berechtigt diese Abstimmung zu beenden!",
                           ephemeral=True)
            return
        votings_channel: i.Channel = await ctx.get_channel()
        voting_message: i.Message = await votings_channel.get_message(self.data[id]["message_id"])
        message_embed: i.Embed = self.evaluate_voting(voting_message)
        current_time_formatted = strftime("%d.%m. %H:%M")
        message_embed.description = "**Diese Abstimmung wurde vorzeitig beendet!**\n" \
            + f"{ctx.user.username}, {current_time_formatted}" \
            + "\n\n" + message_embed.description
        await voting_message.edit(embeds=message_embed)
        del self.data[id]
        self.save_data()
        await ctx.send("Die Abstimmung wurde beendet.", ephemeral=True)

    @i.component_callback("close_voting_menu")
    async def close_voting(self, ctx: i.ComponentContext, ids: list):
        await ctx.defer(ephemeral=True)
        self.load_data()
        for id in ids:
            votings_channel: i.Channel = await ctx.get_channel()
            voting_message: i.Message = await votings_channel.get_message(self.data[id]["message_id"])
            message_embed: i.Embed = self.evaluate_voting(voting_message)
            current_time_formatted = strftime("%d.%m. %H:%M")
            message_embed.description = "**Diese Abstimmung wurde vorzeitig beendet!**\n" \
                + f"{ctx.user.username}, {current_time_formatted}" \
                + "\n\n" + message_embed.description
            await voting_message.edit(embeds=message_embed)
            del self.data[id]
        self.save_data()
        await ctx.edit("Die Abstimmungen wurden beendet.", components=[])


