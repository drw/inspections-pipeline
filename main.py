from typing import Any

import ckanapi
from sqlalchemy import text
from tenacity import retry, stop_after_attempt

from loaders import connect_to_sqlite, make_output_table, save_to_sqlite
from quality_util import check_quality

BASE_URL = "https://data.wprdc.org/"


def clean_query(q: str) -> str:
    """Fix the query so CKAN can run it."""
    import re

    return re.sub("\n", "", re.sub(";", "", q))


@retry(reraise=True, stop=stop_after_attempt(3))
def do_the_query(ckan, query: str, offset: int):
    """Execute CKAN query."""
    return ckan.action.datastore_search_sql(sql=f"{query} OFFSET {offset}")


def query_resource(query: str, site="https://data.wprdc.org") -> list[dict]:
    """This function queries a data table through the CKAN API, continuing to
    increase the offset until all records have been obtained.
    """
    query = clean_query(query)
    ckan = ckanapi.RemoteCKAN(site)
    records = []
    offset = 0
    done = False
    while not done:
        response = do_the_query(ckan, query, offset)
        new_records = response["records"]
        offset += len(new_records)
        records += new_records
        if "records_truncated" not in response or not response["records_truncated"]:
            done = True
        # If the number of records returned is truncated by CKAN's 32000-record limit,
        # there's an extra field in the dictionary called "records_truncated" with value
        # equal to True.

    return records


def get_table_via_api(resource_id: str) -> list[dict]:
    """Get data table through CKAN API."""
    print(f"Fetching contents of resource with ID '{resource_id}' from {BASE_URL}...")
    return query_resource(f'SELECT * FROM "{resource_id}"', BASE_URL)


def remove_key(d, key):
    """Drop key from dictionary."""
    r = dict(d)
    r.pop(key, None)
    return r


def remove_fields(
    data: list[dict[str, Any]], fields: list[str]
) -> list[dict[str, Any]]:
    """Delete fields from records (in list-of-dicts form)."""
    import copy

    filtered = copy.deepcopy(data)
    for field in fields:
        filtered = [remove_key(r, field) for r in filtered]
    return filtered


def print_table(records: list[dict]) -> None:
    """Print tabular data to console."""
    from tabulate import tabulate

    print(tabulate(records, headers="keys"))


def show_table(records: list[dict], name: str, n=10) -> None:
    """Print the first n rows of table to console."""
    if len(records) > n:
        print(f"\nPreview of the first {n} rows of the {name} table.")
        print_table(records[:n])
    else:
        print(f"Preview of the {name} table.")
        print_table(records)


def main() -> None:
    import json
    import os

    from clean_util import clean

    connection = connect_to_sqlite()
    resource_id_by_name = {
        "devices": "21921b0d-8222-44a3-9322-38a6d0f9395f",
        "inspections": "f255d4ef-b6ad-4935-937f-07e36b1c2845",
        "stores": "bac0a05c-71b5-4634-96b9-10cc8a20102d",
    }
    resource_name_by_name = {
        "devices": "Weights and Measures: Devices",
        "inspections": "Weights and Measures: Inspections",
        "stores": "Weights and Measures: Stores",
    }
    records_by_name = {}  # A dict to hold records for later
    # data quality checks.

    table_names = ["inspections", "stores", "devices"]
    for name in table_names:
        resource_name = resource_name_by_name.get(name, name)
        print(f"\n{'=' * 20}Processing {resource_name} data{'=' * 20}".upper())
        # 1) INGEST
        resource_id = resource_id_by_name[name]
        records = get_table_via_api(resource_id)
        # Suppress _full_text column since it's generally visual junk in table output.
        records = remove_fields(records, ["_full_text"])

        print(
            f"Downloaded {len(records)} records from the '{resource_name}' resource."
        )

        # 2a) STORE RAW DATA
        save_to_sqlite(records, f"raw_{name}", connection)

        # Clean records enough to make the output table.
        records = clean(records, name)
        records_by_name[name] = records
        # 2b) STORE CLEANED/MODELLED DATA
        save_to_sqlite(records, name, connection)

        if name != "stores":  # "stores" has too many columns.
            show_table(records, name, 5)
        else:
            print("(Suppressing table preview because the table is too wide.)")

    # 4) ADD DATA QUALITY CHECKS.
    print(f"\n{'=' * 20}RUNNING DATA QUALITY CHECKS FOR ALL TABLES{'=' * 20}")
    for name in table_names:
        check_quality(records_by_name[name], name)

    print(f"\n{'=' * 20}Producing output table{'=' * 20}".upper())
    print(
        "Question: Which fueling locations have the worst fuel-pump-inspection pass rates?\n"
    )
    # 5) PRODUCE ONE OUTPUT TABLE
    make_output_table()

    print(
        "The 20 fueling locations with the worst fuel-pump inspection records, sorted by increasing pass rate:\n"
    )
    query = "SELECT store_name, address, municipality, rate, samples AS inspections, pumps FROM pass_rates LIMIT 20;"
    with connection.connect() as conn:
        resultset = conn.execute(text(query))
        results_as_dict = resultset.mappings().all()
        print_table(results_as_dict)


if __name__ == "__main__":
    main()
