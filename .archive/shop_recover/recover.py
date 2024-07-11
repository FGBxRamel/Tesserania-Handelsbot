import sqlite3 as sql
from Shop import Shop
import interactions as i
import asyncio

bot = i.Client(
    token="", sync_ext=True,
    intents=i.Intents.DEFAULT | i.Intents.GUILD_MEMBERS)


async def main():
    setup()
    channel_id = input("Channel ID: ")
    channel: i.GuildText = await bot.fetch_channel(int(channel_id))
    messages: list[i.Message] = await channel.history(limit=100).flatten()
    for message in messages:
        if len(message.embeds) == 0:
            continue
        embed = message.embeds[0]

        user_select = i.UserSelectMenu(custom_id="owner", max_values=5)
        bot_message = await channel.send(f"Shop: {embed.title}\nBesitzer: ", components=[user_select])
        user_select = await bot.wait_for_component(components=user_select)
        owners: list[i.Member] = user_select.ctx.values
        owners = [int(owner.id) for owner in owners]
        await bot_message.delete()

        if len(message.embeds[0].description) <= 20:
            shop = Shop(
                id=embed.footer.text,
                dc_client=bot,
                name=embed.title,
                offer=embed.fields[0].value,
                location=embed.fields[1].value,
                category=embed.description.replace("||", ""),
                approved=True if embed.fields[3].value == ":white_check_mark:" else False,
                message_id=message.id,
                owners=owners,
                obligatory=True if embed.fields[4].value == ":white_check_mark:" else False
            )
            await shop.create()
        else:
            shop = Shop(
                id=embed.footer.text,
                dc_client=bot,
                name=embed.title,
                offer=embed.description,
                location=embed.fields[1].value,
                category=embed.fields[0].value,
                approved=True if embed.fields[3].value == ":white_check_mark:" else False,
                message_id=message.id,
                owners=owners,
                obligatory=True if embed.fields[4].value == ":white_check_mark:" else False
            )
            await shop.create()


def setup(file: str = "data.db"):
    with sql.connect(file) as conn:
        c = conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS offers (offer_id INTEGER PRIMARY KEY, user_id BIGINT,\
            title TEXT, message_id BIGINT, deadline FLOAT,\
            description TEXT, price TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id))")
        c.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY,\
            offers_count INTEGER, shop_count INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS votings (voting_id INTEGER PRIMARY KEY,\
                  user_id BIGINT, message_id BIGINT, deadline FLOAT,\
                  description TEXT, wait_time FLOAT, create_time FLOAT,\
                  time_type TEXT, initial_deadline FLOAT, count INTEGER,\
                  FOREIGN KEY(user_id) REFERENCES users(user_id))")
        c.execute("CREATE TABLE IF NOT EXISTS shops (shop_id INTEGER PRIMARY KEY,\
                  owners TEXT, name TEXT, offer TEXT, location TEXT,\
                  category TEXT, approved BOOLEAN, message_id BIGINT, obligatory BOOLEAN)")
        c.execute("CREATE TABLE IF NOT EXISTS vacations (ID INTEGER PRIMARY KEY,\
                  user_id BIGINT, start_date BIGINT, end_date BIGINT, reason TEXT,\
                  issuer BIGINT, message_id BIGINT)")
        conn.commit()


@i.listen()
async def on_ready():
    await main()
    # await test()


async def test():
    channel_id = input("Channel ID: ")
    channel: i.GuildText = await bot.fetch_channel(int(channel_id))
    last_message = int(channel.last_message_id)
    while int(channel.last_message_id) == last_message:
        await asyncio.sleep(0.5)
    message = await channel.fetch_message(channel.last_message_id)


bot.start()
