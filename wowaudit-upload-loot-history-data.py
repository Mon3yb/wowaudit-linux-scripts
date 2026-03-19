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
            "Could not find `RCLootCouncilLootDB = { ... }` in the Lua file.",
        ], check=False)
        raise Exception("Could not find `RCLootCouncilLootDB = { ... }` in the Lua file.")
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

###########################################################
# NOTES

# Upload structure
#{ "_json":
#    [
#        "rclootcoundil_id" = "String",
#        "recipient": "String",
#        "master_looter": "String",
#        "difficulty_id": int (14=normal, 15=heroic, 16=mythic, 17=raidfinder),
#        "response": "String"
#        "response_color:" (u8, u8, u8, f32),
#        "awarded_at": "String",
#        "game_strin": "String",
#        "note": "String",
#        "old_item_1_game_string": "OptionString",
#        "old_item_2_game_string": "OptionString",
#        "same_response_amount": "OptionInt32",
#        "wishes_when_awarded": "OptionString"
#    ]
#}

# Json values?
#"rclootcouncil_id" = ???
#"recipient" = "Player": [] <-- json array with everything for that player
#"master_looter": ??? maybe Player['owner']
#"difficulty_id": Player['difficultyID']
#"response": Player['response']
#"response_color": Player['color']
#"awarded_at": Player['time']
#"game_string": Player['lootWon']
#"note": Player['note']
#"old_item_1_game_string": Player['itemReplaced1']
#"old_item_2_game_string": Player['itemReplaced2']
#"same_response_amount": Player['same_response_amount']
#"wishes_when_awarded": Player['wishes']

# History data structure
# "Zelarn-Blackhand": [
#            {
#              "mapID": 2912,
#              "wishes": [
#                {
#                  "p": 0.7,
#                  "s": "b",
#                  "id": 249313,
#                  "sp": 73,
#                  "v": 340
#                }
#              ],
#              "color": [
#                0,
#                1,
#                0,
#                1
#              ],
#              "class": "WARRIOR",
#              "iSubClass": 4,
#              "groupSize": 27,
#              "boss": "Imperator Averzian",
#              "time": "19:32:00",
#              "iClass": 4,
#              "itemReplaced1": "|cnIQ4:|Hitem:251164:8029:::::::90:262::23:5:13439:6652:12699:13577:12782:1:28:3025:::::|h[Amalgamation's Harness]|h|r",
#              "instance": "The Voidspire-Normal",
#              "owner": "Baric-Blackhand",
#              "typeCode": "CATALYST",
#              "response": "Need",
#              "id": "1773858830-5",
#              "difficultyID": 14,
#              "lootWon": "|cnIQ4:|Hitem:249313::::::::90:262::3:4:6652:13577:13333:12785::::::|h[Light-Judged Spaulders]|h|r",
#              "responseID": 1,
#              "date": "2026/03/18",
#              "same_response_amount": 2,
#              "votes": 0,
#              "isAwardReason": false
#            },
#            {
#              "mapID": 2912,
#              "wishes": [
#                {
#                  "p": 0.09,
#                  "s": "b",
#                  "id": 249316,
#                  "sp": 73,
#                  "v": 44
#                }
#              ],
#              "date": "2026/03/18",
#              "class": "WARRIOR",
#              "iSubClass": 4,
#              "groupSize": 27,
#              "votes": 0,
#              "time": "19:45:00",
#              "iClass": 4,
#              "itemReplaced1": "|cnIQ4:|Hitem:266432:7959:::::::90:262::42:2:13577:12787:1:28:4240:::::|h[Silvermoon Suncrest]|h|r",
#              "instance": "The Voidspire-Normal",
#              "owner": "Baric-Blackhand",
#              "typeCode": "default",
#              "response": "Offspec",
#              "id": "1773859593-13",
#              "difficultyID": 14,
#              "lootWon": "|cnIQ4:|Hitem:249316::::::::90:262::3:5:6652:12667:13577:13333:12786::::::|h[Crown of the Fractured Tyrant]|h|r",
#              "responseID": 2,
#              "note": "nur stats",
#              "same_response_amount": 0,
#              "boss": "Fallen-King Salhadaar",
#              "color": [
#                1,
#                0.5,
#                0,
#                1
#              ]
#            },
#            {
#              "mapID": 2912,
#              "wishes": [
#                {
#                  "p": 2.18,
#                  "s": "b",
#                  "id": 249281,
#                  "sp": 73,
#                  "v": 1055
#                }
#              ],
#              "date": "2026/03/18",
#              "class": "WARRIOR",
#              "iSubClass": 7,
#              "groupSize": 27,
#              "boss": "Fallen-King Salhadaar",
#              "time": "19:47:00",
#              "iClass": 2,
#              "itemReplaced1": "|cnIQ4:|Hitem:259958:7982:::::::90:262::42:2:6652:12786:1:28:5236:::::|h[Preyseeker's Longsword]|h|r",
#              "typeCode": "default",
#              "instance": "The Voidspire-Normal",
#              "owner": "Baric-Blackhand",
#              "id": "1773859700-15",
#              "response": "Need",
#              "responseID": 1,
#              "difficultyID": 14,
#              "lootWon": "|cnIQ4:|Hitem:249281::::::::90:262::3:3:42:13333:12786::::::|h[Blade of the Final Twilight]|h|r",
#              "color": [
#                0,
#                1,
#                0,
#                1
#              ],
#              "isAwardReason": false,
#              "same_response_amount": 0,
#              "itemReplaced2": "|cnIQ4:|Hitem:251202::::::::90:262::23:4:13439:6652:12699:12786:1:28:3025:::::|h[Reflux Reflector]|h|r",
#              "votes": 0
#            }

#https://discord.com/channels/278497762516140032/1282960340820426754/1483960375484616927



