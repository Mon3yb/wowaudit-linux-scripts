from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from slpp import slpp as lua

###########################################################
### Variables to change

wow_path = ""  # Path to the _retail_ folder
account_name = ""  # Account name as written in WTF/Account
wow_audit_api_token = ""  # Your API token from WoWAudit

###########################################################
### More variables, normally you don't need to change these

API_URI = "https://wowaudit.com/v1/rclootcouncil"
APP_NAME = "WoWAudit loot history upload script"
MAX_ITEM_AGE_DAYS = 90
REQUEST_TIMEOUT_SECONDS = 30


class WowauditScriptError(RuntimeError):
    """Raised when the loot history upload script cannot complete successfully."""


@dataclass(frozen=True)
class ScriptConfig:
    wow_path: Path
    api_token: str
    account_name: str

    def require_wow_directory(self) -> Path:
        if not self.wow_path.is_dir():
            raise WowauditScriptError(
                "No World of Warcraft instance found. "
                "Please make sure you provided the correct path in the script."
            )
        return self.wow_path

    def require_api_token(self) -> str:
        if not self.api_token.strip():
            raise WowauditScriptError(
                "No WoWAudit API token configured. Please set `wow_audit_api_token` in the script."
            )
        return self.api_token

    def require_account_name(self) -> str:
        if not self.account_name.strip():
            raise WowauditScriptError(
                "No account name configured. Please set `account_name` in the script."
            )
        return self.account_name



def notify(summary: str, body: str, *, critical: bool = False) -> None:
    command = ["notify-send"]
    if critical:
        command.extend(["-u", "critical"])
    command.extend(["-a", APP_NAME, summary, body])
    subprocess.run(command, check=False)



def fail(summary: str, body: str) -> None:
    notify(summary, body, critical=True)
    raise WowauditScriptError(f"{summary}\n{body}")



def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WowauditScriptError(f"Required file not found: {path}") from exc



def extract_lua_assignment(text: str, variable_name: str) -> str:
    match = re.search(rf"\b{re.escape(variable_name)}\s*=\s*({{.*}})\s*$", text, re.S)
    if not match:
        raise WowauditScriptError(
            f"Could not find `{variable_name} = {{ ... }}` in the Lua file."
        )
    return match.group(1)



def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)



def post_json(url: str, *, api_token: str, payload: dict[str, Any], expected_statuses: set[int]) -> requests.Response:
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code not in expected_statuses:
        raise WowauditScriptError(
            f"HTTP request to {url} failed with "
            f"{response.status_code} {response.reason}: {response.text[:200]}"
        )
    return response



def loot_data_path(config: ScriptConfig) -> Path:
    return (
        config.wow_path
        / "WTF"
        / "Account"
        / config.account_name
        / "SavedVariables"
        / "RCLootCouncil.lua"
    )



def extract_loot_history(lua_file: Path) -> dict[str, list[dict[str, Any]]]:
    text = read_text(lua_file)
    raw_assignment = extract_lua_assignment(text, "RCLootCouncilLootDB")

    try:
        decoded_lua = lua.decode(raw_assignment)
        factionrealm = decoded_lua.get("factionrealm")
        if not isinstance(factionrealm, dict) or not factionrealm:
            raise ValueError("Missing factionrealm data in RCLootCouncilLootDB.")
        loot_history = next(iter(factionrealm.values()))
    except Exception as exc:
        raise ValueError("Could not decode RCLootCouncil loot history.") from exc

    if not isinstance(loot_history, dict):
        raise ValueError("Expected loot history to decode to a dictionary keyed by character name.")

    return loot_history



def parse_awarded_at(date_string: str, time_string: str) -> datetime:
    datetime_string = f"{date_string} {time_string}"
    for pattern in ("%d/%m/%y %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(datetime_string, pattern)
        except ValueError:
            continue

    raise ValueError(
        f"Invalid date/time format in loot history: {datetime_string}. "
        "Expected DD/MM/YY HH:MM:SS or YYYY/MM/DD HH:MM:SS."
    )



def normalize_color(color: Any) -> str:
    if not isinstance(color, list) or len(color) != 4:
        color = [0, 0, 0, 1]
    red, green, blue, alpha = color
    return f"{int(red * 255)},{int(green * 255)},{int(blue * 255)},{alpha}"



def build_history_item(character_name: str, item_table: dict[str, Any], *, forced: bool) -> dict[str, Any] | None:
    awarded_at = parse_awarded_at(item_table["date"], item_table["time"])
    cutoff = datetime.now() - timedelta(days=MAX_ITEM_AGE_DAYS)
    if not forced and awarded_at <= cutoff:
        return None

    return {
        "rclootcouncil_id": item_table["id"],
        "recipient": character_name,
        "master_looter": item_table["owner"],
        "difficulty_id": int(item_table["difficultyID"]),
        "response": item_table["response"],
        "response_color": normalize_color(item_table.get("color")),
        "awarded_at": f"{item_table['date']} {item_table['time']}",
        "game_string": item_table["lootWon"],
        "note": item_table.get("note") or "",
        "old_item_1_game_string": item_table.get("itemReplaced1"),
        "old_item_2_game_string": item_table.get("itemReplaced2"),
        "same_response_amount": item_table.get("same_response_amount") or 0,
        "wishes_when_awarded": dump_json(item_table.get("wishes")),
    }



def build_payload(loot_history: dict[str, list[dict[str, Any]]], *, forced: bool = False) -> dict[str, list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    for character_name, character_loot in loot_history.items():
        if not isinstance(character_loot, list):
            raise ValueError(f"Expected loot history list for character {character_name!r}.")
        for item_table in character_loot:
            if not isinstance(item_table, dict):
                raise ValueError(f"Unexpected loot history entry for character {character_name!r}.")
            history_item = build_history_item(character_name, item_table, forced=forced)
            if history_item is not None:
                items.append(history_item)
    return {"_json": items}



def main() -> int:
    try:
        config = ScriptConfig(
            wow_path=Path(wow_path).expanduser(),
            api_token=wow_audit_api_token,
            account_name=account_name,
        )
        config.require_wow_directory()
        config.require_api_token()
        config.require_account_name()

        loot_history = extract_loot_history(loot_data_path(config))
        payload = build_payload(loot_history)
        post_json(API_URI, api_token=config.api_token, payload=payload, expected_statuses={204})

        notify("Successfully ran process", "Loot history uploaded to WoWAudit")
        print("Successfully ran process\nLoot history uploaded to WoWAudit")
        return 0
    except Exception as exc:
        fail("Error in uploading loot history to WoWAudit", str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
