from random import randint
from time import localtime, sleep, strftime, time
import interactions as i
import configparser as cp
import classes.database as db
from sqlite3 import IntegrityError
import re


class Voting():
    def __init__(
            self,
            id: int,
            dc_client: i.Client,
            owner: int = 0,
            message_id: int = 0,
            deadline: float = 0,
            description: str = "Kein Text gesetzt!",
            wait_time: float = 0,
            create_time: float = 0,
            time_type: str = "Tag(e)",
            count: int = 2,
            skip_setup: bool = False
    ) -> None:
        """
        Representation of a voting.
        If skip_setup is True, the voting won't be set up from the database.
        """
        self.id = id
        self.client = dc_client
        self.owner = owner
        self.message_id = message_id
        self.deadline = deadline
        self.description = description
        self.wait_time = wait_time
        self.create_time = create_time
        self.time_type = time_type
        self.count = count
        self._emote_chars = ["\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9", "\U0001F1EA",
                             "\U0001F1EB", "\U0001F1EC", "\U0001F1ED", "\U0001F1EE", "\U0001F1EF"]

        self._refresh_config()
        if not skip_setup:
            if not self._setup(self.id):
                raise ValueError("Voting not found.")

    async def create(self, emotes: list[str] = []) -> None:
        """Creates the voting in the database and the embed.
        If emotes is given it will use the given ones instead."""
        embed = await self._get_embed()
        voting_role = await self._get_voting_role_to_ping()
        message = await self.channel.send(content=voting_role.mention, embed=embed)
        self.message_id = message.id
        try:
            self._save()
        except IntegrityError:
            await message.delete()
            raise ValueError("Voting already exists.")

        if len(emotes) > 0:
            for emote in emotes:
                await message.add_reaction(emote)
        else:
            emote_index = 0
            while self.count > emote_index:
                await message.add_reaction(self._emote_chars[emote_index])
                emote_index += 1
                sleep(0.5)

    async def update(self, notice: bool = True) -> None:
        """Updates the voting in the database and the embed."""
        if notice:
            regex = r"(?:\n*\+bearbeitet\+)"
            exists = re.search(regex, self.description)
            if exists is None:
                self.description += "\n\n+bearbeitet+"
            else:
                subst = "\\n\\n+bearbeitet+"
                self.description = re.sub(
                    regex, subst, self.description, flags=re.MULTILINE)
        db.delete_data("votings", {"voting_id": self.id})
        self._save()
        embed = await self._get_embed()
        message = await self.channel.fetch_message(self.message_id)
        await message.edit(embed=embed)

    async def delete(self) -> None:
        """Deletes the voting from the database and the embed."""
        db.delete_data("votings", {"voting_id": self.id})
        message = await self.channel.fetch_message(self.message_id)
        await message.delete()

    async def close(self) -> None:
        message = await self.channel.fetch_message(self.message_id)
        tie = await self._is_tie()
        if tie:
            ties = await self._get_ties()
            identifier = randint(1000, 9999)
            identifiers = self._get_identifiers()
            while identifier in identifiers:
                identifier = randint(1000, 9999)
            tie_description = f"[Eine Abstimmung]({message.jump_url}) ist unentschieden ausgegangen.\
                Bitte stimme in dieser Abstimmung ab, um den Gewinner zu bestimmen."
            voting = Voting(
                identifier,
                self.client,
                owner=self.owner,
                deadline=time() + self.wait_time,
                description=tie_description,
                wait_time=self.wait_time,
                create_time=time(),
                time_type=self.time_type,
                count=len(ties),
                skip_setup=True
            )
            await voting.create(emotes=ties)
            self.description += f"\n\n**Ergebnis:** Unentschieden! Bitte schaue weiter unten nach."
        else:
            winner, winner_count = "", 0
            for reaction in message.reactions:
                if reaction.count > winner_count:
                    winner, winner_count = reaction.emoji.name, reaction.count
            self.description += f"\n\n**Ergebnis:** {winner}"

        await self.update(notice=False)
        db.delete_data("votings", {"voting_id": self.id})

    def _refresh_config(self):
        """Reloads the relevant config values."""
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            channel_id = config.getint('Voting', 'voting_channel')
            self.channel = self.client.get_channel(channel_id)
            if self.channel is None:
                raise ValueError("Voting channel not found.")
            self._voting_role_to_ping_id = config.getint(
                'Voting', 'ping_role')

    async def _get_embed(self) -> i.Embed:
        """Return the embed of the voting."""
        owner_name = await self._get_owner_name()

        formatted_end_time = strftime(
            "%d.%m. %H:%M", localtime(int(self.deadline)))
        deadline_seconds = int(self.deadline) - int(self.create_time)
        conversion_seconds = {
            "Tag(e)": 86400, "Stunde(n)": 3600, "Minute(n)": 60}
        initial_deadline = round(
            deadline_seconds / conversion_seconds[self.time_type], 2)
        initial_deadline = str(initial_deadline).replace(".", ",")

        embed = i.Embed(
            title="Abstimmung",
            description=f"\n{self.description}",
            color=0xdaa520,
            author=i.EmbedAuthor(
                name=f"{owner_name}, {formatted_end_time} ({initial_deadline} {self.time_type})"),
            footer=i.EmbedFooter(text=str(self.id))
        )
        return embed

    async def _get_owner_name(self) -> str:
        """Returns a string of the name of the owner of the voting."""
        user = await self.client.fetch_user(self.owner)
        return user.display_name

    async def _get_voting_role_to_ping(self) -> i.Role:
        """Returns the role to ping."""
        role = await self.channel.guild.fetch_role(self._voting_role_to_ping_id)
        return role

    def _setup(self, id: int) -> bool:
        """Sets up the voting from the database. Returns True if successful, else False."""
        data = db.get_voting_data(id)
        if data is None:
            return False
        self.owner = data[0]
        self.message_id = data[1]
        self.deadline = data[2]
        self.description = data[3]
        self.wait_time = data[4]
        self.create_time = data[5]
        self.time_type = data[6]
        return True

    def _save(self) -> None:
        """Saves the voting to the database."""
        db.save_data("votings",
                     "voting_id, user_id, message_id, deadline, description, wait_time, create_time, time_type",
                     (self.id, self.owner, self.message_id, self.deadline, self.description,
                      self.wait_time, self.create_time, self.time_type))

    async def _is_tie(self) -> bool:
        message = await self.channel.fetch_message(self.message_id)
        reactions = message.reactions
        counts = [reaction.count for reaction in reactions]
        counts.sort(reverse=True)
        tie = False if counts[0] != counts[1] else True
        return tie

    async def _get_ties(self) -> list[str]:
        message = await self.channel.fetch_message(self.message_id)
        reactions = message.reactions
        counts = [reaction.count for reaction in reactions]
        counts.sort(reverse=True)
        ties = []
        for reaction in reactions:
            if reaction.count == counts[0]:
                ties.append(reaction.emoji.name)
        return ties

    @staticmethod
    def _get_identifiers() -> list[int]:
        """Returns a list of all identifiers of votings in the database."""
        ids = db.get_data("votings", attribute="voting_id", fetch_all=True)
        return [id[0] for id in ids]

    # Getters

    @property
    def id(self):
        return int(self._id)

    @property
    def client(self) -> i.Client:
        return self._client

    @property
    def owner(self):
        return int(self._owner)

    @property
    def message_id(self):
        return int(self._message_id)

    @property
    def deadline(self):
        return float(self._deadline)

    @property
    def description(self):
        return str(self._description)

    @property
    def wait_time(self):
        return float(self._wait_time)

    @property
    def create_time(self):
        return float(self._create_time)

    @property
    def time_type(self):
        return str(self._time_type)

    @property
    def channel(self) -> i.GuildText:
        return self._channel

    @property
    def count(self):
        return int(self._count)

    # Setters
    @id.setter
    def id(self, value):
        self._id = int(value)

    @client.setter
    def client(self, value):
        self._client = value

    @owner.setter
    def owner(self, value):
        self._owner = int(value)

    @message_id.setter
    def message_id(self, value):
        self._message_id = int(value)

    @deadline.setter
    def deadline(self, value):
        self._deadline = float(value)

    @description.setter
    def description(self, value):
        value = str(value).replace("\\n", "\n")
        self._description = str(value)

    @wait_time.setter
    def wait_time(self, value):
        self._wait_time = float(value)

    @create_time.setter
    def create_time(self, value):
        self._create_time = int(value)

    @time_type.setter
    def time_type(self, value):
        control = ["Tag(e)", "Stunde(n)", "Minute(n)"]
        if value not in control:
            raise ValueError(
                f"Time type must be one of the following: {control}")
        self._time_type = str(value)

    @channel.setter
    def channel(self, value):
        self._channel = value

    @count.setter
    def count(self, value):
        if int(value) < 2:
            raise ValueError("Count must be at least 2.")
        self._count = int(value)
