from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
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

API_URI = "https://wowaudit.com/v1/game_data"
APP_NAME = "WoWAudit Guild data script"
REQUEST_TIMEOUT_SECONDS = 30


class WowauditScriptError(RuntimeError):
    """Raised when the guild upload script cannot complete successfully."""


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



def companion_data_path(config: ScriptConfig) -> Path:
    return (
        config.wow_path
        / "WTF"
        / "Account"
        / config.account_name
        / "SavedVariables"
        / "WowauditCompanion.lua"
    )



def extract_payload(lua_file: Path) -> dict[str, list[dict[str, Any]]]:
    text = read_text(lua_file)
    raw_assignment = extract_lua_assignment(text, "WowauditDataSyncDB")

    try:
        decoded_lua = lua.decode(raw_assignment)
    except Exception as exc:
        raise ValueError("Could not decode Lua payload to Python data.") from exc

    if not isinstance(decoded_lua, dict):
        raise ValueError("Expected WowauditDataSyncDB to decode to a dictionary.")

    return {"_json": [decoded_lua]}



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

        payload = extract_payload(companion_data_path(config))
        post_json(API_URI, api_token=config.api_token, payload=payload, expected_statuses={200})

        notify("Successfully ran process", "Guild data uploaded to WoWAudit")
        print("Successfully ran process\nGuild data uploaded to WoWAudit")
        return 0
    except Exception as exc:
        fail("Error in uploading guild data to WoWAudit", str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
