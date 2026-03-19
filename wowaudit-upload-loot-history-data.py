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
            json_data = lua.decode(data.group(1)) #decode into json
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

def process_history_item(
    character_name: str,
    item_table: dict,
    forced: bool):

    loot_history_item = {}
        try:
            date = item_table['date']
            time = item_table['time']
            datetime = f"{date} {time}" #<----- TODO: Need to check for "%d/%m/%y %H:%M:%S" or "%Y/%m/%d %H:%M:%S" and needs to be string

            seconds_since_epoch = #UTC.now as timestamp <----- TODO
            three_months_ago = #UTC.now - 90 days as timestamp <----- TODO

            # Check if data is older than 3 months and return nothing if it is
            if not forced and (three_months_ago >= seconds_since_epoch):
                return

            #TODO: process values and check for none. Maybe use dict.get('data') instead of json['data'] for better handling e.g. "dict.get('data') or None"
            rclootcouncil_id = item_table['id']
            recipient = character_name
            master_looter item_table['owner']
            difficulty_id = item_table['difficultyID']
            response = item_table['response']
            rgba = f"{item_table[0]*255}, {item_table[1]*255}, {item_table[2]*255}, {item_table[3]}"  #<----- NOTE: Needs to be in format of "r,g,b,a". each color from 0-255 and a = 0.0-1.0 in decimals
            awarded_at = datetime
            game_string = item_table['lootWon']
            note = item_table['note'] #<----- NOTE: Need to "None" empty string if nothing
            old_item_1_game_string = item_table[itemReplaced1] #<----- NOTE: Need to "None" if nothing
            old_item_2_game_string = item_table[itemReplaced2] #<----- NOTE: Need to "None" if nothing
            same_response_amount = item_table[same_response_amount] #<----- NOTE: Need to "None" if nothing
            wishes_when_awarded = item_table['wishes'] #<----- NOTE: Need to "None" if nothing

            loot_history_item =(
                f"""rclootcouncil_id" = {rclootcouncil_id}\n""",
                f"""recipient": {recipient}""",
                f"""master_looter": {master_looter}""",
                f"""difficulty_id": {int(difficulty_id)}""",
                f"""response": {response}"""
                f"""response_color: {rgba}""",
                f"""awarded_at": {awarded_at}""",
                f"""game_string": {game_string}""",
                f"""note": {note}""",
                f"""old_item_1_game_string": {old_item_1_game_string}""",
                f"""old_item_2_game_string": {old_item_2_game_string}""",
                f"""same_response_amount": {same_response_amount}""",
                f"""wishes_when_awarded": {wishes_when_awarded}"""
            )
            return loot_history_item
        except:
            subprocess.run([
                "notify-send",
                "-u","critical",
                "-a", "WoWAudit Guild data script",
                "Error in item parsing",
                "Could not parse item in history table",
            ], check=False)
            raise Exception(f"Could not parse item in history table")



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

#fn process_history_item(
#        &self,
#        character_name: String,
#        item_table: LuaTable,
#        forced: bool,
#    ) -> Result<LootHistoryItem, Box<dyn std::error::Error>> {
#        let date: String = item_table.get("date")?;
#        let time: String = item_table.get("time")?;
#        let datetime =
#            NaiveDateTime::parse_from_str(&format!("{} {}", date, time), "%d/%m/%y %H:%M:%S")
#                .or_else(|_| NaiveDateTime::parse_from_str(&format!("{} {}", date, time), "%Y/%m/%d %H:%M:%S"))?;
#        let seconds_since_epoch = datetime.and_utc().timestamp() as i32;
#
#        let three_months_ago = (Utc::now() - Duration::days(90)).timestamp() as i32;
#        if !forced && three_months_ago >= seconds_since_epoch {
#            return Err("Item is older than 3 months".into());
#        }
#
#        let wishes: Result<LuaTable, LuaError> = item_table.get("wishes");
#        let wish_json = match wishes {
#            Ok(wishes) => Some(serde_json::to_string(&wishes)?),
#            _ => None,
#        };
#
#        let wow_color: LuaTable = item_table.get("color")?;
#        let r: f32 = wow_color.get(1)?;
#        let g: f32 = wow_color.get(2)?;
#        let b: f32 = wow_color.get(3)?;
#        let a: f32 = wow_color.get(4)?;
#        let rgba = ((r * 255.0) as u8, (g * 255.0) as u8, (b * 255.0) as u8, a);
#
#        Ok(LootHistoryItem {
#            rclootcouncil_id: item_table.get("id")?,
#            recipient: character_name,
#            master_looter: item_table.get("owner")?,
#            difficulty_id: item_table.get("difficultyID")?,
#            response: item_table.get("response")?,
#            response_color: rgba,
#            game_string: item_table.get("lootWon")?,
#            note: item_table.get("note").unwrap_or("".to_string()),
#            awarded_at: datetime.to_string(),
#            old_item_1_game_string: item_table.get("itemReplaced1").unwrap_or(None),
#            old_item_2_game_string: item_table.get("itemReplaced2").unwrap_or(None),
#            wishes_when_awarded: wish_json,
#            same_response_amount: item_table.get("same_response_amount").unwrap_or(None),
#        })
#    }

# Upload structure
#{ "_json":
#    [
#        "rclootcoundil_id" = "String",
#        "recipient": "String",
#        "master_looter": "String",
#        "difficulty_id": int,
#        "response": "String"
#        "response_color:" "String(r(255), g(255), b(255), a(0.0-1))",
#        "awarded_at": "String",
#        "game_string": "String",
#        "note": "String",
#        "old_item_1_game_string": "String",
#        "old_item_2_game_string": "String",
#        "same_response_amount": int,
#        "wishes_when_awarded": "String"
#    ]
#}

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



