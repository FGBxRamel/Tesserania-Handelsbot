import sqlite3 as sql

# Beware: All of this is not sufficient to stop SQL injection, but enough for this bot


def get_data(table: str, *conditions: dict, attribute: str = '*', fetch_all: bool = False) -> tuple:
    con = sql.connect("data.db")
    cur = con.cursor()
    attribute = attribute.replace(';', '')
    table = table.replace(';', '')
    if len(conditions) == 0:
        cur.execute(f"SELECT {attribute} FROM {table}")
    else:
        conditions = conditions[0]
        statement = f"SELECT {attribute} FROM {table} WHERE "
        for attr in conditions:
            statement += f"{attr} = ? AND "
        statement = statement[:-5]
        cur.execute(statement, tuple(conditions.values()))
    if fetch_all:
        return cur.fetchall()
    else:
        return cur.fetchone()


def save_data(table: str, attributes: str, values: tuple):
    table = table.replace(';', '')
    attributes = attributes.replace(';', '')
    safer_values = (i.replace(";", "") for i in values)
    con = sql.connect("data.db")
    cur = con.cursor()
    statement = f"INSERT INTO {table} ({attributes}) VALUES {values}"
    cur.execute(statement)
    con.commit()


def delete_data(table: str, conditions: dict):
    table = table.replace(';', '')
    con = sql.connect("data.db")
    cur = con.cursor()
    statement = f"DELETE FROM {table} WHERE "
    for attr in conditions:
        statement += f"{attr} = ? AND "
    statement = statement[:-5]
    cur.execute(statement, tuple(conditions.values()))
    con.commit()


def update_data(table: str, attribute: str, value, conditions: dict):
    table = table.replace(';', '')
    attribute = attribute.replace(';', '')
    con = sql.connect("data.db")
    cur = con.cursor()
    statement = f"UPDATE {table} SET {attribute} = ? WHERE "
    for attr in conditions:
        statement += f"{attr} = ? AND "
    statement = statement[:-5]
    value_tuple = (value,) + tuple(conditions.values())
    cur.execute(statement, value_tuple)
    con.commit()
