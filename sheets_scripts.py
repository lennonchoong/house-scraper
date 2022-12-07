import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

with open("./config.json") as f:
    config = json.load(f)

creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file(
        "token.json", ["https://www.googleapis.com/auth/spreadsheets"]
    )


def write_to_sheet(listings):
    try:
        service = build("sheets", "v4", credentials=creds)

        date_added = datetime.today().strftime("%d-%m-%Y")

        # Call the Sheets API
        rows = [list(row.values()) + [date_added] for row in listings]
        service.spreadsheets().values().append(
            spreadsheetId=config["SPREADSHEET_ID"],
            range="Sheet1!A:Z",
            body={"majorDimension": "ROWS", "values": rows},
            valueInputOption="USER_ENTERED",
        ).execute()
    except HttpError as err:
        print(err)


def get_listing_ids():
    try:
        service = build("sheets", "v4", credentials=creds)
        existing_ids = set()
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=config["SPREADSHEET_ID"], range="A1:A")
            .execute()
        )
        values = result.get("values", [])
        existing_ids.update([x[0] for x in values[1:]])
        return existing_ids
    except HttpError as err:
        print(err)