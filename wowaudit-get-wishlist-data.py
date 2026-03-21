from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

###########################################################
### Variables to change

wow_path = ""  # Path to the _retail_ folder
wow_audit_api_token = ""  # Your API token from WoWAudit

###########################################################
### More variables, normally you don't need to change these

WISHLIST_API_URI = "https://wowaudit.com/v1/rclootcouncil"
TEAM_API_URI = "https://wowaudit.com/v1/team"
APP_NAME = "WoWAudit wishlist update"
REQUEST_TIMEOUT_SECONDS = 30


class WowauditScriptError(RuntimeError):
    """Raised when the wishlist update script cannot complete successfully."""


@dataclass(frozen=True)
class ScriptConfig:
    wow_path: Path
    api_token: str

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


def notify(summary: str, body: str, *, critical: bool = False) -> None:
    command = ["notify-send"]
    if critical:
        command.extend(["-u", "critical"])
    command.extend(["-a", APP_NAME, summary, body])
    subprocess.run(command, check=False)



def fail(summary: str, body: str) -> None:
    notify(summary, body, critical=True)
    raise WowauditScriptError(f"{summary}\n{body}")



def fetch_json(url: str, *, api_token: str) -> dict[str, Any]:
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise WowauditScriptError(
            f"HTTP request to {url} failed with "
            f"{response.status_code} {response.reason}: {response.text[:200]}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise WowauditScriptError(f"Response from {url} was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise WowauditScriptError(f"Expected a JSON object from {url}, but received {type(payload).__name__}.")

    return payload



def build_paths(config: ScriptConfig) -> tuple[Path, Path]:
    addon_path = config.wow_path / "Interface" / "AddOns" / "RCLootCouncil_wowaudit"
    wishlist_path = addon_path / "Data" / "db.lua"
    return addon_path, wishlist_path



def local_data_is_stale(output_path: Path, wishlist_payload: dict[str, Any]) -> bool:
    if not output_path.is_file():
        return True

    local_db = output_path.read_text(encoding="utf-8")
    local_timestamp_match = re.search(r"wowauditTimestamp\s*=\s(\d+)", local_db)
    if local_timestamp_match is None:
        return True

    api_timestamp = int(wishlist_payload["updated_timestamp"])
    local_timestamp = int(local_timestamp_match.group(1))
    return api_timestamp > local_timestamp



def build_lua_payload(wishlist_payload: dict[str, Any], team_payload: dict[str, Any]) -> str:
    timestamp = wishlist_payload["updated_timestamp"]
    difficulties = wishlist_payload["difficulties"]
    wishlist_data = wishlist_payload["wishlist_data"]
    team_id = team_payload["id"]

    return (
        f"wowauditTimestamp = {timestamp}\n"
        f"teamID = {team_id}\n"
        f"difficulties = {difficulties}\n"
        f"wishlistData = {wishlist_data}\n"
    )



def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)



def main() -> int:
    try:
        config = ScriptConfig(wow_path=Path(wow_path).expanduser(), api_token=wow_audit_api_token)
        config.require_wow_directory()
        config.require_api_token()

        addon_path, wishlist_path = build_paths(config)
        if not addon_path.is_dir():
            fail(
                "Addon folder not found",
                f"Please make sure the Addon RCLootCouncil_wowaudit is installed at {config.wow_path}",
            )

        wishlist_payload = fetch_json(WISHLIST_API_URI, api_token=config.api_token)
        team_payload = fetch_json(TEAM_API_URI, api_token=config.api_token)

        if local_data_is_stale(wishlist_path, wishlist_payload):
            write_text_atomic(wishlist_path, build_lua_payload(wishlist_payload, team_payload))

            message = (
                f"Successfully updated wishlist data\n"
                f"Total characters: {wishlist_payload['character_amount']}\n"
                f"Total wishes: {wishlist_payload['wish_amount']}"
            )
            notify("Successfully updated wishlist data", message)
            print(message)
            return 0

        message = "Successfully ran process\nLocal data already up to date"
        notify("Successfully ran process", "Local data already up to date")
        print(message)
        return 0
    except Exception as exc:
        fail("WoWAudit wishlist update failed", str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
