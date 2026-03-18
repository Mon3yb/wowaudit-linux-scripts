import json
import re
import subprocess
import requests
from pathlib import Path
from slpp import slpp as lua #lua parser

###########################################################
### Variables to change

wow_path = "" #Path to the _retail_ folder e.g "/home/mon3y/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/"
account_name = "" #Account name as written in "WTF/Account" e.g. ""/home/mon3y/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/WTF/Account/MON3Y" = "MON3Y"
wow_audit_api_token = "" #Your API token from WoWAudit. Get it from the website (https://wowaudit.com) in the API menu under Credentials

###########################################################
### More variables, normaly you don't need to change these

api_uri = "https://wowaudit.com/v1/"
rclootcouncil_data_path = Path(f"{wow_path}/WTF/Account/{account_name}/SavedVariables/RCLootCouncil.lua")

###########################################################
# Functions

#RCLootCouncilLootDB = {}
def extract_loot_history_table(lua_file: file) -> dict:
    with open(lua_file, "r") as f:
        text = f.read()

    data = re.search(r"\bRCLootCouncilLootDB\s*=\s*({.*})\s*$", text, re.S)

    if not data:
        subprocess.run([
            "notify-send",
            "-u","critical",
            "-a", "WoWAudit Guild data script",
            "Error in parsing Lua",
            "Could not find `WowauditDataSyncDB = { ... }` in the Lua file.",
        ], check=False)
        raise Exception("Could not find `WowauditDataSyncDB = { ... }` in the Lua file.")
    else:
        try:
            decoded_lua = lua.decode(data.group(1))
            json_data = {"_json": [decoded_lua]}

        except:
            subprocess.run([
                "notify-send",
                "-u","critical",
                "-a", "WoWAudit Guild data script",
                "Error in parsing Lua",
                "Could not decode lua to json",
            ], check=False)
            raise Exception(f"Could not decode lua to json")
        return json_data

def upload_loot_history_data(api_uri: str, api_token: str, data: dict) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }

    response = requests.post(api_uri, headers=headers, json=data, timeout=30)

    if response.status_code == 200:
        return response
    else:
        subprocess.run([
            "notify-send",
            "-u","critical",
            "-a", "WoWAudit loot history upload script",
            f"Error in uploading loot history to WoWAudit",
            f"{response.status_code} {response.reason} {response.text[:200]}",
        ], check=False)
        response.raise_for_status()

#DEBUG, will be replaced with real stuff ;)
#output_path = "/home/mon3y/Dokumente/history_test.json"
#data = extract_loot_history_table(rclootcouncil_data_path)
#with open(output_path, "w") as f:
#    json.dump(data, f,ensure_ascii=False,indent=2)

###########################################################
# Main
#payload = extract_loot_history_table(rclootcouncil_data_path)
#upload_loot_history_data(api_uri, wow_audit_api_token, payload)




