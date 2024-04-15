import interactions as i
import configparser as cp
from datetime import datetime
from time import time
from classes.database import save_data

user_select_data = {}
scope_ids = []
with open('config.ini', 'r') as config_file:
    config = cp.ConfigParser()
    config.read_file(config_file)
    scope_ids = config.get('General', 'servers').split(',')
reason: list[i.SlashCommandChoice] = []
for r in config.get('Vacation', 'reasons').split('|'):
    reason.append(i.SlashCommandChoice(name=r, value=r))


class UrlaubCommand(i.Extension):
    def __init__(self, client):
        self.elevatedUsers = {"updateTime": time(), "users": set()}

    def _getDMUsers(self, ctx: i.SlashContext) -> list[i.Member]:
        """Searches all users of a guild that have the DM role and returns them as a list.
        It caches the list so we don't pull it every time."""
        dm_roles: list[i.Role] = []
        for role_id in config.get('Vacation', 'dm_roles').split(','):
            dm_roles.append(ctx.guild.get_role(int(role_id)))

        dm: set[i.Member] = set((role.members for role in dm_roles))

        self.elevatedUsers["updateTime"] = time()
        self.elevatedUsers["users"] = dm
        return dm

    def _isUserElevated(self, user: i.Member) -> bool:
        """Checks if a user is elevated and returns True if they are."""
        if time() - self.elevatedUsers["updateTime"] > 300 or len(self.elevatedUsers["users"]) == 0:
            self.elevatedUsers["users"] = self._getDMUsers(user)
        return user in self.elevatedUsers["users"]

    @i.slash_command(name="urlaub",
                     description="Der Command für das Eintragen von Urlauben.",
                     scopes=scope_ids)
    @i.slash_option(
        name="nutzer",
        opt_type=i.OptionType.USER,
        description="Der Nutzer, für den der Urlaub eingetragen werden soll.",
        required=True
    )
    @i.slash_option(
        name="grund",
        description="Der Grund für den Urlaub.",
        opt_type=i.OptionType.STRING,
        required=True,
        choices=reason
    )
    @i.slash_option(
        name="beginn",
        description="Der Beginn des Urlaubs.",
        opt_type=i.OptionType.STRING,
        required=True
    )
    @i.slash_option(
        name="ende",
        description="Das Ende des Urlaubs.",
        opt_type=i.OptionType.STRING,
        required=True
    )
    async def urlaub(self, ctx: i.SlashContext, nutzer: i.Member, grund: str, beginn: str, ende: str):
        if not self._isUserElevated(ctx.author) and nutzer != ctx.author:
            await ctx.send("Du hast keine Berechtigung, Urlaub für andere einzutragen!", ephemeral=True, delete_after=5)
            return
        try:
            converted_start_date = datetime.strptime(beginn, '%d.%m.%Y')
            converted_end_date = datetime.strptime(ende, '%d.%m.%Y')
        except ValueError:
            await ctx.send("Das Datum muss im Format dd.mm.yyyy sein!", ephemeral=True, delete_after=10)
            return

        embed = i.Embed(title="Urlaubsinfo",
                        description=f"**Wer?**\n{nutzer.display_name}",
                        fields=[
                            i.EmbedField(
                                name="Grund", value=grund),
                            i.EmbedField(
                                name="Beginn", value=converted_start_date.strftime('%d.%m.%Y')),
                            i.EmbedField(
                                name="Ende", value=converted_end_date.strftime('%d.%m.%Y'))
                        ])
        guild_channel = ctx.guild.get_channel(
            int(config.get('Vacation', 'guild_channel')))
        guild_message = await guild_channel.send(embed=embed)

        embed.fields.append(i.EmbedField(
            name="Ersteller", value=ctx.author.display_name))
        for member in self._getDMUsers(ctx):
            dm_channel: i.DM = await member.fetch_dm()
            await dm_channel.send(embed=embed)

        # Save the vacation in the database
        # Save vacation in database
        save_data('vacations', 'user_id, start_date, end_date, reason, issuer, message_id',
                  (int(nutzer.id),
                   converted_start_date.timestamp(),
                   converted_end_date.timestamp(),
                   grund,
                   int(ctx.author.id),
                   int(guild_message.id)))

        await ctx.send("Urlaub eingetragen!", ephemeral=True, delete_after=10)
