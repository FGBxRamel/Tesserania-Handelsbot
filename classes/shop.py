import interactions as i
import classes.database as db
import configparser as cp
from sqlite3 import IntegrityError


class Shop():
    def __init__(
        self,
        id: int,
        dc_client: i.Client,
        channel: i.GuildText,
        name: str = None,
        offer: str = None,
        location: str = None,
        dm_description: str = None,
        category: str = None,
        approved: bool = False,
        message_id: int = None,
        owners: list[str | int] | str | int = None,
        skip_setup: bool = False
    ) -> None:
        """
        Representation of a shop.
        If skip_setup is True, the shop won't be set up from the database.
        """
        self.id = int(id)
        self.client = dc_client
        self.channel = channel
        self.name = str(name) if name else None
        self.offer = str(offer) if offer else None
        self.location = str(location) if location else None
        self.dm_description = str(
            dm_description) if dm_description else None
        self.category = str(category) if category else None
        self.approved = bool(approved)
        self.message_id = int(message_id) if message_id else None
        if type(owners) is str or type(owners) is int:
            self.owners = [owners]
        elif type(owners) is list:
            self.owners = [int(owner) for owner in owners]

        self._refresh_config()
        if not skip_setup:
            sucess = self._setup(self.id)
            if not sucess:
                raise ValueError("Shop not found.")

    def _refresh_config(self):
        with open('config.ini', 'r') as config_file:
            config = cp.ConfigParser()
            config.read_file(config_file)
            self.categories_excluded_from_limit = config.get(
                'Shops', 'categories_excluded_from_limit').split(",")
            self.categories_excluded_from_limit = [
                category.strip() for category in self.categories_excluded_from_limit]

    async def update(self) -> None:
        """Updates the shop in the database and the embed."""
        # I know recreating is not the best option, but sufficient for this case.
        db.delete_data("shops", {"shop_id": self.id})
        db.save_data("shops", "name, offer, location, dm_description, category, approved,\
                     message_id, owners, shop_id",
                     (self.name, self.offer, self.location, self.dm_description,
                      self.category, self.approved, self.message_id,
                      ",".join([str(owner) for owner in self.owners]), self.id))
        message = await self.channel.fetch_message(self.message_id)
        embed = await self._get_embed()
        await message.edit(embed=embed)

    async def delete(self) -> None:
        """Deletes the shop from the database, the embed and set the owner counts."""
        db.delete_data("shops", {"shop_id": self.id})
        message = await self.channel.fetch_message(self.message_id)
        await message.delete()
        if self.category not in self.categories_excluded_from_limit:
            for owner in self.owners:
                db.decrease_shop_count(owner)

    async def create(self) -> None:
        """Creates the shop in the database, the embed and sets the owner counts."""
        embed = await self._get_embed()
        message = await self.channel.send(embed=embed)
        self.message_id = int(message.id)
        try:
            db.save_data("shops", "shop_id, name, offer, location, dm_description, category, approved, message_id, owners",
                         (self.id, self.name, self.offer, self.location, self.dm_description,
                          self.category, self.approved, self.message_id, ",".join([str(owner) for owner in self.owners])))
        except IntegrityError:
            await message.delete()
            raise ValueError("Shop already exists.")
        if self.category not in self.categories_excluded_from_limit:
            for owner in self.owners:
                db.increase_shop_count(int(owner))

    async def approve(self) -> None:
        """Approves the shop."""
        self.approved = True
        await self.update()

    async def deny(self) -> None:
        """Denies the shop."""
        self.approved = False
        await self.update()

    def set_id(self, id: int) -> None:
        """Sets the id of the shop."""
        self.id = int(id)

    def set_name(self, name: str) -> None:
        """Sets the name of the shop."""
        self.name = str(name)

    def set_offer(self, offer: str) -> None:
        """Sets the offer of the shop."""
        self.offer = str(offer)

    def set_location(self, location: str) -> None:
        """Sets the location of the shop."""
        self.location = str(location)

    def set_dm_description(self, dm_description: str) -> None:
        """Sets the dm_description of the shop."""
        self.dm_description = str(dm_description)

    def set_category(self, category: str) -> None:
        """Sets the category of the shop."""
        self.category = str(category)

    def set_owners(self, owner: str | int | list[str | int]) -> None:
        """Sets the owners of the shop."""
        if type(owner) is str or type(owner) is int:
            self.owners = [owner]
        elif type(owner) is list:
            self.owners = [int(owner) for owner in owner]

    def get_embed(self) -> i.Embed:
        """Returns the embed of the shop."""
        return self._get_embed()

    def _setup(self, id: int) -> bool:
        """Sets up the shop if it's found in the database.
        Returns True if the shop was found, False otherwise."""
        shop = db.get_shop_data(id)
        if shop is None:
            return False
        self.name = shop[0]
        self.offer = shop[1].replace("\\n", "\n")
        self.location = shop[2]
        self.dm_description = shop[3]
        self.category = shop[4]
        self.approved = bool(shop[5])
        self.message_id = int(shop[6])
        self.owners = [int(owner) for owner in shop[7].split(",")]
        return True

    async def _get_embed(self) -> i.Embed:
        """Return the embed of the shop."""
        owners = await self._get_owner_names()
        embed = i.Embed(
            title=self.name,
            description=f"|| *{self.category}* ||\n",
            color=0xdaa520,
            footer=str(self.id)
        )
        embed.add_field(
            name="Angebot",
            value=self.offer,
            inline=False
        )
        embed.add_field(
            name="Ort",
            value=self.location,
            inline=False
        )
        embed.add_field(
            name="Besitzer",
            value=owners,
            inline=False
        )
        embed.add_field(
            name="Genehmigt",
            value=":white_check_mark:" if self.approved else ":x:",
            inline=False
        )
        return embed

    async def _get_owner_names(self) -> str:
        """Returns a string of the names of the owners of the shop."""
        name_str = ""
        for owner in self.owners:
            user: i.User = await self.client.fetch_user(owner)
            name_str += user.display_name + ", "
        return name_str[:-2]
