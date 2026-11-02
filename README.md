# Everyone loves piplines

## Overview

The script iterates through the three tables in the Allegheny County Weights and Measures Inspections dataset, pulling the data through the CKAN API, saving the raw versions of the tables to a SQLite database, cleaning the tables (somewhat), and saving the cleaned tables to the SQLite file too, reporting all its progress via console output. It then performs some data quality checks on the cleaned records. Finally, the script joins the three tables to generate a new table designed to answer a question about the inspections data and prints out a sample of the result.

## Installation and Operation

```
> python -m pip install -r requirements.txt

> python main.py
```

## Cleaning notes and data quality issues

To fix the fact that `device_type` values that should have been identical were fragmented into title case (e.g. "Tape Measure") and all caps ("TAPE MEASURE") variants, I standardized this field by converting all values to all caps. The same transformation was applied to a few other fields.

Another problem  that needed to be addressed was the presence of extra spaces, such as multiple spaces between the value and units in the `capacity` field (e.g., "30  LB") or trailing spaces (such as the value "8 " appearing in the `pump` field, distinguishing it from the more common "8" value).

I used a regex to split space-less `capacity` strings like "30LB", adding a space between the numerical value and the units.

I ultimately did enough cleaning to make the data usable for the purpose of this assignment, but there is more cleaning that could be done to make the data more usable.

While there are a couple of data quality checks that enforce controlled vocabularies on particular fields, for the most part, the checks just enforce the above cleaning requirements.

## Design Decisions

1) **Downloading data:** I considered pulling the data from the /datastore/dump/ API endpoint. This is because I noticed that the WPRDC data portal was sometimes failing to load pages (or datastore table views) in the browser because of 502 Bad Gateway errors, and my initial thought was that getting all the data in one API request might be a good idea to minimize the chance of such broken connections.

    However, I realized that, if the frequency of connection errors were sufficiently high, it would be better to download the data in the chunk size allowed by the CKAN server; this is because downloading, say 7 million records of an 8-million record table, only to be interrupted by an error will take longer than downloading the first 7 million records in small chunks and then getting interrupted on the *n*th chunk and having to retry it. Also, if one is downloading a sufficiently large set of data, there are situations where it may overtax the CKAN server to do it all in one fell swoop. Pulling the data in chunks through the CKAN API will take more HTTP requests and will add some (possibly inconsequential) amount of time (in the situation that no errors interrupt the data transmission), but the download process will be more robust.

    I also used the `tenacity` Python library, which makes it easy to add decorators to functions to automate retries in case of failure.

2) **Data storage:** I wanted a data storage approach that would be lightweight, easy to deploy, and capable of supporting the SQL queries that I expected to run in answering the data question. I chose SQLite, though DuckDB would have also worked.

3) **Data quality checks:** I started by writing data quality checks in Python, but decided that it would be convenient to use a framework given the repetitive nature of the data-quality-checking code. After experimenting with the Great Expectations library, I decided to use the more obscure [cuallee](https://github.com/canimus/cuallee) data quality checking library because of its more concise syntax and the relative ease with which I was able to implement custom data quality checks.

## The Data Question

I decided to investigate gas pump inspections. I was curious about the variation in the pass rate for fuel pumps since a higher rate of malfunctioning fuel pumps could be of interest to both consumers and County inspectors. To reduce this to an easily answered question, I narrowed this down to "Which fueling locations have the worst fuel-pump-inspection pass rates?"

A short table is presented when running main.py; the full results of the query are in the SQLite database, in the table named `pass_rates`.

The numbers of pumps and inspections were included to give a sense of the amount of data that was available for that station, though I think that inspections per pump may be a more useful metric for judging the amount of evidence for rows in the output table.

It's worth noting that of the 422 fueling locations, 54 have perfect 100% pass rates, and some of those have had hundreds of inspections.

One dimension I didn't have the chance to dig into was time. The Inspections table represents more than 10 years of activity, and the recency and distribution of inspection failures in time is an important consideration.

## Caveats and Limitations

I'm using the maximum value in the `pump` column from the Devices table as a proxy for the number of fuel pumps at each gas station. It has been consistent with the apparent number of pumps in the cases I've checked, but this should be more carefully checked.

While I tried to eliminate non-commercial fueling locations, it would have been time-consuming to check all of the locations with fuel dispensers, so there are a number of locations that are no regular gas stations in the `pass_rates` table.

## What I'd Do Differently...
### ...with Daily Data Refreshes

As written, the script would not handle schema changes well. To guard against problems caused by changes to the schemas of the WPRDC data tables, I'd just modify the script to start by deleting the SQLite table, to start fresh each day.

To handle scheduling, retries on failure, and logging, I'd probably modify the script to run under an orchestrator like Airflow for best reliability.

### ...at 100x Scale

As the number of rows gets much larger, at some point it would make sense to add indexes to speed up the query and switch to a more performant database (like Postgres).

I'd also check with the data steward to see how often the historical data in the Inspections table changes. To reduce the cost and duration of the updates, I'd consider using a SQL query to selectively pull and update only recent inspections on a daily basis, with less frequent complete refreshes of the local version of the inspections table.

(Under these circumstances, I'd have to forgo my plan to wipe the database tables at the beginning of each script run. Instead, I'd compare the source data schema with the destination data schema and trigger an exception and alert for schema mismatches.)

## AI disclosure

No AI tools were used in working on this assignment.
