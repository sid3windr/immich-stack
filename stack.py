#!/usr/bin/env python3

"""
Immich Stacking Tool.

See README.md and the command line help for more information.
Copyright (c) 2025 Tom Laermans.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""


import requests
from urllib.parse import urljoin
import os
import sys
import argparse
import configparser

PREFERRED_PRIMARY_EXTS = {".jpg", ".jpeg", ".jpe"}


def load_config():
    """Load Immich configuration from immich.ini or environment variables."""
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.path.dirname(__file__), "immich.ini")

    if not os.path.exists(ini_path):
        raise FileNotFoundError(f"Config file not found: {ini_path}")

    config.read(ini_path)

    IMMICH_URL = config.get("immich", "url", fallback=os.environ.get("IMMICH_URL", "http://localhost:2283"))
    API_KEY = config.get("immich", "api_key", fallback=os.environ.get("IMMICH_API_KEY"))

    if not API_KEY:
        sys.exit("Error: Immich API key not set. Use immich.ini or IMMICH_API_KEY environment variable.")

    return IMMICH_URL, API_KEY


def get_duplicate_groups(IMMICH_URL, API_KEY):
    """Fetch duplicate asset groups from Immich API."""
    endpoint = urljoin(IMMICH_URL, "api/duplicates")
    HEADERS = {
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }
    resp = requests.get(endpoint, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def filter_dupe_pairs(duplicate_groups):
    """Filter groups that have exactly 2 assets and identical filenames excluding extension."""
    results = []
    for group in duplicate_groups:
        assets = group.get("assets", [])
        if len(assets) != 2:
            continue
        names = [asset.get("originalPath") or asset.get("filename") or "" for asset in assets]
        ids = [asset.get("id") for asset in assets]

        # Normalize to just filename
        basenames = [os.path.splitext(os.path.basename(name))[0] for name in names]
        exts = [os.path.splitext(name)[1].lower() for name in names]

        if not basenames[0] or not basenames[1]:
            continue

        if basenames[0] != basenames[1]:
            # different file name, ignore
            continue

        if exts[0] == exts[1]:
            # same extension, ignore
            continue

        # Decide ordering so first id becomes primary:
        # Prefer JPEG as primary if present (useful for RAW+JPG pairs).
        primary_index = 0
        if exts[1] in PREFERRED_PRIMARY_EXTS and exts[0] not in PREFERRED_PRIMARY_EXTS:
            primary_index = 1
        elif exts[0] in PREFERRED_PRIMARY_EXTS and exts[1] not in PREFERRED_PRIMARY_EXTS:
            primary_index = 0
        else:
            # neither or both preferred -> keep original order (assets[0] first)
            primary_index = 0

        ordered_ids = [ids[primary_index], ids[1 - primary_index]]
        ordered_paths = [names[primary_index], names[1 - primary_index]]

        results.append({"ids": ordered_ids, "paths": ordered_paths, "exts": [exts[primary_index], exts[1 - primary_index]]})

    return results


def stack_assets(IMMICH_URL, API_KEY, asset_ids):
    """Stack assets together in Immich (using the first asset as the primary)."""
    endpoint = urljoin(IMMICH_URL, "api/stacks")
    HEADERS = {
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }
    payload = {"assetIds": asset_ids}
    resp = requests.post(endpoint, headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stack Immich duplicates with identical filenames (ignoring extension).")

    # Require either --stack or --dry-run
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stack", action="store_true", help="Find duplicates with identical filenames and stack them")
    group.add_argument("--dry-run", action="store_true", help="Only print duplicates, do not stack them.")

    parser.add_argument('--verbose', '-v', action='count', default=0, help='Increase verbosity')

    args = parser.parse_args()

    IMMICH_URL, API_KEY = load_config()
    duplicates = get_duplicate_groups(IMMICH_URL, API_KEY)
    dupe_pairs = filter_dupe_pairs(duplicates)

    if dupe_pairs:
        for pair in dupe_pairs:
            if args.dry_run or args.verbose:
                print(f"Found pair: {pair['paths'][0]}  ↔  {pair['paths'][1]}")
            if args.dry_run:
                print("   [dry-run] Would stack these.")
            else:
                result = stack_assets(IMMICH_URL, API_KEY, pair["ids"])
                if args.verbose:
                    print(f"   ✅ Stacked to {result['primaryAssetId']}")
    else:
        if args.dry_run or args.verbose:
            print("No matching duplicates found.")
