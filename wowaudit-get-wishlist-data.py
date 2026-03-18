import re
import subprocess
import requests
from pathlib import Path

###########################################################
### Variables to change

wow_path = "" #Path to the _retail_ folder e.g "/home/mon3y/Faugus/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/"
wow_audit_api_token = "" #Your API token from WoWAudit. Get it from the website (https://wowaudit.com) in the API menu under Credentials

###########################################################
### More variables, normaly you don't need to change these

wishlist_api_uri = "https://wowaudit.com/v1/rclootcouncil"
team_api_uri = "https://wowaudit.com/v1/team"
addon_path = Path(f"{wow_path}/Interface/AddOns/RCLootCouncil_wowaudit")
wishlist_path = Path(f"{addon_path}/Data/db.lua")
###########################################################
# Functions

def get_wishlist_data(api_uri: str, api_token: str) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }

    response = requests.get(api_uri, headers=headers, timeout=30)

    if response.status_code == 200:
        return response.json()
    else:
        subprocess.run([
            "notify-send",
            "-u","critical",
            "-a", "WoWAudit wishlist update",
            f"Error in retrieving wishlist data from WoWAudit",
            f"{response.status_code} {response.reason} {response.text[:200]}",
        ], check=False)
        response.raise_for_status()

def get_team_data(api_uri: str, api_token: str) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }

    response = requests.get(api_uri, headers=headers, timeout=30)

    if response.status_code == 200:
        return response.json()
    else:
        subprocess.run([
            "notify-send",
            "-u","critical",
            "-a", "WoWAudit wishlist update",
            f"Error in retrieving team data from WoWAudit",
            f"{response.status_code} {response.reason} {response.text[:200]}",
        ], check=False)
        response.raise_for_status()

def check_updated_timestamp(output_path: str, data:dict) -> bool:
    if Path(output_path).is_file():
        with open(output_path, "r") as f:
            local_db = f.read()
            local_timestamp = re.search(r'wowauditTimestamp\s\=\s(\d+)', local_db)
            api_timestamp = data['updated_timestamp']

            if local_timestamp and local_timestamp != None:
                if int(api_timestamp) > int(local_timestamp.group(1)):
                    return True
                else:
                    return False
            else:
                return True #return true if local_timestamp is not found

def write_to_db_lua(output_path: str, wishlist_data: dict, team_data: dict ) -> None:
    timestamp = wishlist_data['updated_timestamp']
    difficulties = wishlist_data['difficulties']
    wishlist_data = wishlist_data['wishlist_data']
    team_id = team_data['id']

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
    wishlist_response = get_wishlist_data(wishlist_api_uri, wow_audit_api_token)
    team_response = get_team_data(team_api_uri, wow_audit_api_token)

    if check_updated_timestamp(wishlist_path, wishlist_response):
        try:
            write_to_db_lua(wishlist_path, wishlist_response, team_response)
        except:
            subprocess.run([
                "notify-send",
                "-u","critical",
                "-a", "WoWAudit wishlist update",
                f"Error in retrieving wishlist data from WoWAudit",
                f"{wishlist_response.status_code} {wishlist_response.reason} {wishlist_response.text[:200]}",
            ], check=False)
            raise Exception(f"Error in retrieving wishlist data from WoWAudit\n{wishlist_response.status_code} {wishlist_response.reason} {wishlist_response.text[:200]}")

        subprocess.run([
            "notify-send",
            "-a", "WoWAudit wishlist update",
            f"Successfully updated wishlist data",
            f"Total characters: {wishlist_response['character_amount']}",
            f"Total wishes: {wishlist_response['wish_amount']}"
        ], check=False)
        print(f"Successfully updated wishlist data\nTotal characters: {wishlist_response['character_amount']}\nTotal wishes: {wishlist_response['wish_amount']}")
    else:
        subprocess.run([
            "notify-send",
            "-a", "WoWAudit wishlist update",
            f"Successfully ran process",
            f"Local data already up to date"
        ], check=False)
        print(f"Successfully ran process\nLocal data already up to date")
