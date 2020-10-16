import json
import os
import sys

PAR_DIR = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(PAR_DIR, os.path.pardir)))

from crudder import Crudder  # noqa: E402
from airbase.utils import Logger  # noqa: E402
from google.oauth2.service_account import Credentials  # noqa: E402


logger = Logger.start(__name__)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# resource directories
ASSETS_DIR = os.path.join(PAR_DIR, "assets")
SCHEMAS_DIR = os.path.join(PAR_DIR, "schemas")
CREDENTIALS = Credentials.from_service_account_file(
    "/Users/lparis2/repos/lfparis-38bcd64cccea.json", scopes=scopes
)
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")


def extractor(schema: str, task: str, *args, **kwargs) -> None:
    """
    1. Retrieve data from Snowflake
    2. Post new data to Airtable/Sheets
    3. Update Airtable/Sheets data
    4. Delete invalid data

    Args:
        schema: name of .json schema file
        task: source filename without extension
    """

    # get data
    with open(os.path.join(SCHEMAS_DIR, schema)) as fp:
        schema = json.load(fp)

    schema_by_task = {
        task["source"]["filename"][
            : -len(task["source"]["filetype"]) - 1
        ]: task
        for task in schema["tasks"]
    }

    task = schema_by_task[task]

    # get source
    source_filename = os.path.join(ASSETS_DIR, task["source"]["filename"])
    source_filetype = task["source"]["filetype"]
    if source_filetype == "csv":
        df = Crudder.get_csv_data(source_filename)
    elif source_filetype == "sql":
        pass
    else:
        return

    # If Google Sheets, get data in list of lists (1st row is headers)
    if schema["type"] == "sheets":
        data = Crudder.convert_df(df, output="rows")

    # If Airtable, get data in list of dictionaries
    elif schema["type"] == "airtable":
        data = Crudder.convert_df(df, output="records")

    task.update(
        {
            "credentials": AIRTABLE_API_KEY
            if schema["type"] == "airtable"
            else CREDENTIALS,
            "id": schema["id"],
            "prefix": schema.get("prefix"),
        }
    )

    # Create, Read, Update, Delete
    Crudder.crud(data, schema["type"], **task)
