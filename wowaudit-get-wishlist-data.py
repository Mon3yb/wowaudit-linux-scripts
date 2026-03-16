import re
import subprocess
import requests
from pathlib import Path

###########################################################
### Variables to change

wow_path = "" #Path to the _retail_ folder e.g "/home/mon3y/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/"
wow_audit_api_token = "" #Your API token from WoWAudit. Get it from the website (https://wowaudit.com) in the API menu under Credentials

#Your team id. This is a bit hidden. Open the wishlist on the website, then inspect the page, go to the Network tab and search for "teams/"
#The filepaths include your team id. eg. https://wowaudit.com/api/guilds/11111/teams/<<YOUR-TEAM-ID>>/loot_wishlist.......
wishlist_team_id = ""

###########################################################
### More variables, normaly you don't need to change these

api_uri = "https://wowaudit.com/v1/rclootcouncil"
addon_path = Path(f"{wow_path}/Interface/AddOns/RCLootCouncil_wowaudit")
wishlist_path = Path(f"{addon_path}/Data/db.lua")

###########################################################
# Functions

def get_api_data(api_uri: str, api_token: str) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }

    response = requests.get(api_uri, headers=headers, timeout=30)

    if response.status_code == 200:
        wishlist_data = response.json()
        return wishlist_data
    else:
        subprocess.run([
            "notify-send",
            "-u","critical",
            "-a", "WoWAudit wishlist update",
            f"Error in retrieving wishlist data from WoWAudit",
            f"{response.status_code} {response.reason} {response.text[:200]}",
        ], check=False)
        response.raise_for_status()

def check_updated_timestamp(output_path: str, data:dict) -> bool:
    if Path(output_path).is_file():
        with open(output_path, "r") as f:
            local_db = f.read()
            local_timestamp = re.search(r'wowauditTimestamp\s\=\s(\d+)', local_db).group(1)
            api_timestamp = data['updated_timestamp']

            if int(api_timestamp) > int(local_timestamp):
                return True
            else:
                return False

def write_to_db_lua(output_path: str, data: dict, team_id: str ) -> None:
    timestamp = data['updated_timestamp']
    difficulties = data['difficulties']
    wishlist_data = data['wishlist_data']

    lua_string = (
        f"""wowauditTimestamp = {timestamp}\n"""
        f"""teamID = {team_id}\n"""
        f"""difficulties = {difficulties}\n"""
        f"""wishlistData = {wishlist_data}\n"""
    )

    with open(output_path, "w") as f:
        f.write(lua_string)

###########################################################
### Main

if not Path(wow_path).is_dir():
    subprocess.run([
        "notify-send",
        "-u","critical",
        "-a", "WoWAudit wishlist update",
        f"No World of Warcraft instance found",
        f"Please make sure you provided the correct path in the script",
    ], check=False)
    raise Exception(f"No World of Warcraft instance found\nPlease make sure you provide the correct path in the script")
elif not Path(addon_path).is_dir():
    subprocess.run([
        "notify-send",
        "-u","critical",
        "-a", "WoWAudit wishlist update",
        f"Addon folder not found",
        f"Please make sure the Addon RCLootCouncil_wowaudit is installed at {wow_path}",
    ], check=False)
    raise Exception(f"Addon folder not found\nPlease make sure the Addon RCLootCouncil_wowaudit is installed at {wow_path}")
else:
    response = get_api_data(api_uri, wow_audit_api_token)
    if check_updated_timestamp(wishlist_path, response):
        try:
            write_to_db_lua(wishlist_path, response, wishlist_team_id)
        except:
            subprocess.run([
                "notify-send",
                "-u","critical",
                "-a", "WoWAudit wishlist update",
                f"Error in retrieving wishlist data from WoWAudit",
                f"{response.status_code} {response.reason} {response.text[:200]}",
            ], check=False)
            raise Exception(f"Error in retrieving wishlist data from WoWAudit\n{response.status_code} {response.reason} {response.text[:200]}")

        subprocess.run([
            "notify-send",
            "-a", "WoWAudit wishlist update",
            f"Successfully updated wishlist data",
            f"Total characters: {response['character_amount']}",
            f"Total wishes: {response['wish_amount']}"
        ], check=False)
        print(f"Successfully updated wishlist data\nTotal characters: {response['character_amount']}\nTotal wishes: {response['wish_amount']}")
    else:
        subprocess.run([
            "notify-send",
            "-a", "WoWAudit wishlist update",
            f"Successfully ran process",
            f"Local data already up to date"
        ], check=False)
        print(f"Successfully ran process\nLocal data already up to date")
