from typing import Any

# ANSI escape codes for formatting console output:
RED = "\033[91m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
RESET = END = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
BRIGHT_YELLOW = "\033[93m"


def require_case(record: dict[str, Any], field: str, case: str) -> bool:
    """Check that the case of the value for the given field and
    record match that passed in `case`. Return a boolean (True if
    the string case is valid, otherwise False). This boolean
    can be used as a surrogate for the number of errors found
    (True => 1, False => 0). If record[field] is None, return True.
    """

    if record[field] is None:
        return True
    if case in ["all caps", "uppercase"]:
        return record[field] == record[field].upper()
    if case == "title case":
        return record[field] == record[field].title()
    if case == "lowercase":
        return record[field] == record[field].lower()

    raise ValueError(f'require_case() has no test defined for case == "{case}".')


def check_quality(records: list[dict[str, Any]], name: str) -> None:
    """When using this function, pass the records to be checked for errors
    as well as the "name" variable to indicate which table is being examined.
    """
    import pandas as pd
    from cuallee import Check

    def has_char_after_number(df: pd.DataFrame) -> pd.DataFrame:
        """This is a custom data check that detects cases
        where a number is immediately followed by a letter. It was
        designed specifically for the `capacity` column and will trigger
        on cases such as "30LB".
        """
        import re

        def has_space_if_num(x: Any) -> bool:
            if x is None:
                return True
            if re.match(r"^\d", str(x)) is None:
                return True
            return re.match(r"^\d+[A-Za-z]", str(x)) is None

        return df.assign(test=(df["capacity"].apply(has_space_if_num)))

    def no_leading_zero_integers(df: pd.DataFrame) -> pd.DataFrame:
        """This is a custom data check that detects cases where the capacity
        string starts with a zero, then has one or more digits, and then either
        a space or a letter. Importantly, a decimal point is not allowed in
        this regex. So '0.3 LB' would be valid, but '03 LB' would not.
        """
        import re

        def not_invalid_int(x: Any) -> bool:
            return re.search(r"^0\d+[\sA-Za-z]", str(x)) is None

        return df.assign(test=(df["capacity"].apply(not_invalid_int)))

    if name == "devices":
        check = Check(level=0)  # level = 0 triggers a Warning-level alert.
        check.is_contained_in("deleted", ["0", "1"])

        # Fields that should be all-caps, to force consolidation of,
        # e.g., "Tape Measure" and "TAPE MEASURE".
        check.has_pattern("device_type", "^[^a-z]*$", options={"name": "All-caps"})
        check.has_pattern("device_group", "^[^a-z]*$", options={"name": "All-caps"})
        check.is_custom(
            "capacity",
            no_leading_zero_integers,
            options={"name": "No numbers starting with 0"},
        )
        check.is_custom(
            "capacity",
            has_char_after_number,
            options={"name": "Space between val & units"},
        )
    elif name == "inspections":
        check = Check(level=0)
        check.is_contained_in("result", ["Pass", "Fail"])
    elif name == "stores":
        check = Check(level=0)
        check.has_pattern("new_municipality", "^[^a-z]*$", options={"name": "All-caps"})

    df = pd.DataFrame(records)
    quality_report = check.validate(df)

    # Print data quality report to console.
    print(f'\n{UNDERLINE}Data quality report for "{name}" table{END}\n')
    print(quality_report)

    # Print out data-quality violations.
    for row in quality_report.to_dict(orient="records"):
        if row["status"] == "FAIL":
            if row["level"] == "WARNING":
                color = YELLOW
            elif row["level"] == "ERROR":
                color = RED

            print(
                f"{color}{BOLD}{row['column']}:{END}{color} The {row['rule']} rule failed on {row['violations']} rows.{END}"
            )
