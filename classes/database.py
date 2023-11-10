import sqlite3 as sql

# Beware: All of this is not sufficient to stop SQL injection, but enough for this bot


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
                    FOREIGN KEY(user_id) REFERENCES users(user_id))")
        c.execute("CREATE TABLE IF NOT EXISTS shops (shop_id INTEGER PRIMARY KEY,\
                  owners TEXT, name TEXT, offer TEXT, location TEXT,\
                  category TEXT, approved BOOLEAN, message_id BIGINT, obligatory BOOLEAN)")
        conn.commit()


def get_data(table: str, *conditions: dict, attribute: str = '*', fetch_all: bool = False) -> list[tuple] | tuple | None:
    """Returns data from the database. If fetch_all is True, it returns a list of tuples,
    else a single tuple or None if no entry is found."""
    with sql.connect("data.db") as con:
        cur = con.cursor()
        attribute = attribute.replace(';', '')
        table = table.replace(';', '')
        if len(conditions) == 0:
            cur.execute(f"SELECT {attribute} FROM {table}")
        else:
            conditions = conditions[0]
            statement = f"SELECT {attribute} FROM {table} WHERE "
            delete_attr = []
            for attr in conditions:
                if type(conditions[attr]) is list:
                    # This is bad. To avoid serious injury, stop looking at this.
                    statement += f"{attr} IN ("
                    for value in conditions[attr]:
                        statement += f"""'{value}', """
                    statement = statement[:-2]
                    statement += ") AND "
                    delete_attr.append(attr)
                else:
                    statement += f"{attr} = ? AND "
            for attr in delete_attr:
                del conditions[attr]
            statement = statement[:-5]
            cur.execute(statement, tuple(conditions.values()))
        if fetch_all:
            return cur.fetchall()
        return cur.fetchone()


def save_data(table: str, attributes: str, values: tuple) -> None:
    """Saves data to the database."""
    table = table.replace(';', '')
    attributes = attributes.replace(';', '')
    with sql.connect("data.db") as con:
        cur = con.cursor()
        statement = f"INSERT INTO {table} ({attributes}) VALUES ( "
        for _ in values:
            statement += "?, "
        statement = statement[:-2] + ")"
        cur.execute(statement, values)
        con.commit()


def delete_data(table: str, conditions: dict) -> None:
    """Deletes data from the database."""
    table = table.replace(';', '')
    with sql.connect("data.db") as con:
        cur = con.cursor()
        statement = f"DELETE FROM {table} WHERE "
        for attr in conditions:
            statement += f"{attr} = ? AND "
        statement = statement[:-5]
        cur.execute(statement, tuple(conditions.values()))
        con.commit()


def update_data(table: str, attribute: str, value, conditions: dict) -> None:
    """Updates data in the database."""
    table = table.replace(';', '')
    attribute = attribute.replace(';', '')
    with sql.connect("data.db") as con:
        cur = con.cursor()
        statement = f"UPDATE {table} SET {attribute} = ? WHERE "
        for attr in conditions:
            statement += f"{attr} = ? AND "
        statement = statement[:-5]
        value_tuple = (value,) + tuple(conditions.values())
        cur.execute(statement, value_tuple)
        con.commit()


def get_shop_data(id: int):
    return get_data("shops", {"shop_id": id},
                    attribute="name, offer, location, category,\
                        approved, message_id, owners, obligatory")


def increase_shop_count(user_id: int) -> None:
    if get_data("users", {"user_id": user_id}) is None:
        save_data("users", "user_id, offers_count, shop_count",
                  (int(user_id), 0, 1))
    else:
        user_count = get_data(
            "users", {"user_id": user_id}, attribute="shop_count")[0]
        update_data("users", "shop_count", int(
            user_count) + 1, {"user_id": user_id})


def decrease_shop_count(user_id: int) -> None:
    try:
        user_count = get_data(
            "users", {"user_id": user_id}, attribute="shop_count")[0]
    except TypeError:
        raise ValueError(f"User with ID {user_id} does not exist.")
    if user_count == 0:
        raise ValueError(f"User with ID {user_id} has no shops.")
    update_data("users", "shop_count", int(
        user_count) - 1, {"user_id": user_id})
