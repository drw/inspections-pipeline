import sqlalchemy

DEFAULT_SQLITE_PATH = "sqlite:///default.db"


def connect_to_sqlite(filepath: None | str = None) -> sqlalchemy.engine.base.Engine:
    """Returns SQLAlchemy connection to SQLite file."""
    if filepath is None:
        sqlite_path = DEFAULT_SQLITE_PATH
    else:
        sqlite_path = "sqlite://"
        if "/" != sqlite_path[0]:
            sqlite_path += "/"
        sqlite_path += filepath
    connection = sqlalchemy.create_engine(sqlite_path)
    return connection


def save_to_sqlite(
    records: list[dict], name: str, conn: sqlalchemy.engine.base.Engine
) -> None:
    """Store the records in `records` under the table name `name`.
    The filepath to the SQLite file may be provided; otherwise the default
    database file will be used.
    """

    import pandas as pd

    df = pd.DataFrame(records)

    df.to_sql(name, con=conn, if_exists="delete_rows", index=False)  # Setting
    # if_exists to 'delete_rows' ensures that the table will be overwritten every
    # time this function is called.

    print(
        f'Saved {len(records)} records in table named "{name}" in SQLite database at {conn.url}.'
    )


def make_output_table() -> None:
    """Uses SQL query to generate a new table to answer a question."""
    from sqlalchemy import create_engine, text

    engine = create_engine(DEFAULT_SQLITE_PATH)
    connection = engine.connect()

    with connection.begin() as conn:
        connection.execute(text("BEGIN TRANSACTION;"))
        connection.execute(text("DROP TABLE IF EXISTS pass_rates;"))
        connection.execute(
            text("""
        CREATE TABLE pass_rates AS

            WITH
              fd AS (
                SELECT
                  device_id,
                  store_id,
                  pump
                FROM
                  devices
                WHERE
                  device_group = 'FUEL DISPENSER' -- Limit to gas pumps
                  AND pump REGEXP '^[0-9]+$' -- Drop a few pumps w/non-numeric IDs
                  AND deleted = "0" -- Exclude old non-inspected devices
              ) -- CTE: Just inspected gas pumps w/numeric IDs
            SELECT
              fd.store_id AS store_id,
              AVG(
                CASE
                  WHEN i.result = "Pass" THEN 1
                  ELSE 0
                END
              ) AS rate,
              MAX(CAST(fd.pump AS INTEGER)) AS pumps, -- Gives number of pumps
              COUNT(1) AS samples, -- Number of inspections by store
              COUNT(1)/MAX(CAST(fd.pump AS FLOAT)) as inspections_per_pump,
              s.store_name AS store_name,
              s.address AS address,
              s.municipality AS municipality
            FROM
              fd
              JOIN inspections AS i ON fd.device_id = i.device_id
              JOIN stores AS s ON i.store_id = s.store_id
            WHERE
              s.store_name NOT LIKE "%PARK%"
            GROUP BY
              s.store_id
            ORDER BY
              rate

        ;""")
        )

        # query in one-liner format: WITH fd AS (SELECT device_id, store_id, pump FROM devices WHERE device_group = 'FUEL DISPENSER' AND pump REGEXP '^[0-9]+$' AND deleted = "0") SELECT fd.store_id AS store_id, AVG(CASE WHEN i.result = "Pass" THEN 1 ELSE 0 END) AS rate, MAX(CAST(fd.pump AS INTEGER)) AS pumps, COUNT(1) AS samples, COUNT(1)/MAX(CAST(fd.pump AS FLOAT)) as inspections_per_pump, s.store_name AS store_name, s.address AS address, s.municipality AS municipality FROM fd JOIN inspections AS i ON fd.device_id = i.device_id JOIN stores AS s ON i.store_id = s.store_id WHERE s.store_name NOT LIKE "%PARK%" GROUP BY s.store_id ORDER BY rate

        conn.commit()
