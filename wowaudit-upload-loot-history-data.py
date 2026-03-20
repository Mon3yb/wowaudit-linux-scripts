import json
import re
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta
from slpp import slpp as lua #lua parser

###########################################################
### Variables to change

wow_path = "" #Path to the _retail_ folder e.g "/home/mon3y/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/"
account_name = "" #Account name as written in "WTF/Account" e.g. ""/home/mon3y/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/WTF/Account/MON3Y" = "MON3Y"
wow_audit_api_token = "" #Your API token from WoWAudit. Get it from the website (https://wowaudit.com) in the API menu under Credentials

###########################################################
### More variables, normaly you don't need to change these

api_uri = "https://wowaudit.com/v1/rclootcouncil"
rclootcouncil_data_path = Path(f"{wow_path}/WTF/Account/{account_name}/SavedVariables/RCLootCouncil.lua")

###########################################################
# Functions
def extract_loot_history_dict(lua_file: Path | str) -> dict:
    '''
    Extracting the loot history from RCLootCoundil.lua inside "RCLootCouncilLootDB = { ... }"
    Convert it to a dict
    '''
    with open(lua_file, "r", encoding="utf-8") as f:
        text = f.read()

    rcl_loot_db = re.search(r"\bRCLootCouncilLootDB\s*=\s*({.*})\s*$", text, re.S) # Extract RCLootCouncilLootDB = { ... } from file

    # Check if data is not empty
    if not rcl_loot_db:
        subprocess.run(
            [
                "notify-send",
                "-u", "critical",
                "-a", "WoWAudit Guild data script",
                "Error in parsing Lua",
                "Could not find `RCLootCouncilLootDB = { ... }` in the Lua file.",
            ],
            check=False,
        )
        raise ValueError("Could not find `RCLootCouncilLootDB = { ... }` in the Lua file.")

    try:
        rcl_db_data = rcl_loot_db.group(1)
        rcl_db_dict = lua.decode(rcl_db_data)
        rcl_db_factionrealm = rcl_db_dict.get("factionrealm")
        rcl_loot_history = next(iter(rcl_db_factionrealm.values()))
        return rcl_loot_history
    except Exception as e:
        subprocess.run(
            [
                "notify-send",
                "-u", "critical",
                "-a", "WoWAudit Guild data script",
                "Error in parsing Lua",
                "Could not decode lua to dict",
            ],
            check=False,
        )
        raise ValueError(f"Could not decode lua to dict: {e}") from e


def parse_date_time(date_string: str, time_string: str) -> datetime:
    datetime_string = f"{date_string} {time_string}"
    valid_datetime_formats = [
        "%d/%m/%y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for datetime_format in valid_datetime_formats:
        try:
            return datetime.strptime(datetime_string, datetime_format)
        except ValueError:
            pass

    raise ValueError(
        f'Invalid date or time format in loot history\n'
        f'Expected {valid_datetime_formats[0]} or {valid_datetime_formats[1]} '
        f'but got "{datetime_string}"'
    )


def process_history_item(character_name: str, item_table: dict, forced: bool) -> dict | None:
    try:
        date_string = item_table["date"]
        time_string = item_table["time"]
        datetime_string = f"{date_string} {time_string}"
        datetime_date = parse_date_time(date_string, time_string)
        three_months_ago = datetime.now() - timedelta(days=90)

        if not forced and datetime_date <= three_months_ago:
            print("Item data older than 90 days. Skipping to next one")
            return None

        color = item_table.get("color", [0, 0, 0, 1])
        rgba = f"{int(color[0] * 255)},{int(color[1] * 255)},{int(color[2] * 255)},{color[3]}"

        return {
            "rclootcouncil_id": item_table["id"],
            "recipient": character_name,
            "master_looter": item_table["owner"],
            "difficulty_id": int(item_table["difficultyID"]),
            "response": item_table["response"],
            "response_color": rgba,
            "awarded_at": datetime_string,
            "game_string": item_table["lootWon"],
            "note": item_table.get("note") or "",
            "old_item_1_game_string": item_table.get("itemReplaced1"),
            "old_item_2_game_string": item_table.get("itemReplaced2"),
            "same_response_amount": item_table.get("same_response_amount") or 0,
            "wishes_when_awarded": json.dumps(item_table.get("wishes"), ensure_ascii=False),
        }

    except Exception as e:
        subprocess.run(
            [
                "notify-send",
                "-u", "critical",
                "-a", "WoWAudit Guild data script",
                "Error in item parsing",
                "Could not parse item in history table",
            ],
            check=False,
        )
        raise ValueError(f"Could not parse item in history table\n{e}") from e


def upload_loot_history_data(api_uri: str, api_token: str, data: dict) -> requests.Response:
    """
    HTTP POST request to upload loot history to the rclootcouncil endpoint.
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }

    response = requests.post(api_uri, headers=headers, json=data, timeout=30)

    if response.status_code == 204:
        return response

    subprocess.run(
        [
            "notify-send",
            "-u", "critical",
            "-a", "WoWAudit loot history upload script",
            "Error in uploading loot history to WoWAudit",
            f"{response.status_code} {response.reason} {response.text[:200]}",
        ],
        check=False,
    )
    response.raise_for_status()

###########################################################
## Main
try:
    loot_history = extract_loot_history_dict(rclootcouncil_data_path)

    payload = {"_json": []}
    for character_name, character_loot in loot_history.items():
        for item in character_loot:
            history_item = process_history_item(character_name, item, False)
            if history_item is not None:
                payload["_json"].append(history_item)

    upload_loot_history_data(api_uri, wow_audit_api_token, payload)

    subprocess.run(
        [
            "notify-send",
            "-a", "WoWAudit loot history upload",
            "Successfully ran process",
            "Loot history uploaded to WoWAudit",
        ],
        check=False,
    )
    print("Successfully ran process\nLoot history uploaded to WoWAudit")
except Exception as e:
    subprocess.run(
        [
            "notify-send",
            "-u", "critical",
            "-a", "WoWAudit loot history upload script",
            "Error in uploading loot history to WoWAudit",
            str(e),
        ],
        check=False,
    )
    raise


