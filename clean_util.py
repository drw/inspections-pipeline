from typing import Any


def uppercase_if_not_none(s: str) -> str:
    """Convenience function for uppercasing stings but not nulls."""
    if s is None:
        return s
    return s.upper()


def clean_strings(record: dict[str, Any], field: str) -> str:
    """Remove leading and trailing spaces and replace multiple
    consecutive spaces with just one.
    """
    import re

    if record[field] is not None:
        record[field] = re.sub(r"\s+", " ", record[field])  # Eliminate double spaces.
        record[field] = record[field].strip()  # Eliminate leading and trailing spaces.
    return record[field]


def clean(records: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    """When using this function, pass the records to be cleaned
    as well as the "name" variable to indicate which table is being worked on.
    """
    import re
    from copy import deepcopy

    fix_by_error = {
        "03 LB": "30 LB",
        "3O LB": "30 LB",
        "5O LB": "50 LB"
        }

    cleaned = []
    for record in deepcopy(records):
        if name == "devices":
            # There are pump values like "8 ", which need to be stripped of trailing spaces
            # so they can be grouped with "8".
            for field in ["pump", "capacity"]:
                record[field] = clean_strings(record, field)

            if field == "capacity" and record[field] is not None:
                for error, fix in fix_by_error.items():
                    if record[field] == error:
                        record[field] = fix
                if re.search(r"\d+[A-Z]", record[field]) is not None:
                    # Convert strings like "30LB" to "30 LB"
                    a = re.match(r"(\d+)([A-Z].*)", record[field])
                    if a is not None:
                        record[field] = a.group(1) + " " + a.group(2)

            # Capitalization conversions
            all_caps_fields = ["device_type", "device_group", "capacity"]
            for field in all_caps_fields:
                record[field] = uppercase_if_not_none(record[field])
                # For the capacity field, this fixes a few bogus values
                # ("1510 g" and "6100 g") which deviate from the predominant
                # capitalization of units in this dataset.

        if name == "stores":
            for field in ["address"]:
                record[field] = clean_strings(record, field)
            all_caps_fields = ["new_municipality"]
            for field in all_caps_fields:
                record[field] = uppercase_if_not_none(record[field])

        cleaned.append(record)
    return cleaned
