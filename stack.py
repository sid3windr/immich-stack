#!/usr/bin/env python3

"""
Immich Stacking Tool.

See README.md and the command line help for more information.
Copyright (c) 2025-2026 Tom Laermans.

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
import re

CANONICAL_RE = re.compile(r'^([A-Za-z]+_\d{8}_\d+)')
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


def get_duplicates(IMMICH_URL, API_KEY):
    """Fetch duplicate asset groups from Immich API."""
    endpoint = urljoin(IMMICH_URL, "api/duplicates")
    HEADERS = {
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }
    resp = requests.get(endpoint, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def is_similar_filename(filenames):
    """
    Returns True if the two filenames represent the same logical file
    but have different extensions.
    """
    if len(filenames) != 2:
        raise ValueError("Function requires exactly two filenames")

    def canonical_basename(filename):
        stem = os.path.splitext(os.path.basename(filename))[0]

        match = CANONICAL_RE.match(stem)
        if match:
            return match.group(1)

        # Fallback: strip variant suffixes
        return re.split(r'[.-]', stem, maxsplit=1)[0]

    # Normalize to just filename
    basenames = [canonical_basename(f) for f in filenames]
    exts = [os.path.splitext(f)[1].lower() for f in filenames]

    if not basenames[0] or not basenames[1]:
        # no basename found for either
        return False

    if basenames[0] != basenames[1]:
        # different file name, ignore
        return False

    if exts[0] == exts[1]:
        # same extension, ignore
        return False

    return True


def filter_dupe_pairs(duplicates):
    """Filter groups that have exactly 2 assets and identical filenames excluding extension."""
    results = []
    for group in duplicates:
        assets = group.get("assets", [])
        if len(assets) != 2:
            continue

        names = [asset.get("originalPath") or asset.get("filename") or "" for asset in assets]
        ids = [asset.get("id") for asset in assets]

        # Check similarity of filename, skip if decided to be too different
        if not is_similar_filename(names):
            continue

        # Decide ordering so first id becomes primary, based on extension:
        # Prefer JPEG as primary if present (useful for RAW+JPG pairs).
        exts = [os.path.splitext(name)[1].lower() for name in names]

        primary_index = 0
        if exts[1] in PREFERRED_PRIMARY_EXTS and exts[0] not in PREFERRED_PRIMARY_EXTS:
            primary_index = 1
        elif exts[0] in PREFERRED_PRIMARY_EXTS and exts[1] not in PREFERRED_PRIMARY_EXTS:
            primary_index = 0
        else:
            # Neither or both preferred -> keep original order (assets[0] first)
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


def get_all_album_ids(IMMICH_URL, API_KEY):
    """Fetch all album IDs."""
    endpoint = urljoin(IMMICH_URL, "api/albums")
    HEADERS = {
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }
    resp = requests.get(endpoint, headers=HEADERS)
    resp.raise_for_status()

    # Return album IDs only
    return [item["id"] for item in resp.json()]


def get_assets_in_album(IMMICH_URL, API_KEY, album_id):
    """Fetch assets from the specified album."""
    endpoint = urljoin(IMMICH_URL, f"api/albums/{album_id}")
    HEADERS = {
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }
    resp = requests.get(endpoint, headers=HEADERS)
    resp.raise_for_status()
    album = resp.json()

    # Store only the filename paths, and sort them so we can actually match similar ones
    assets = sorted(album.get("assets", []), key=lambda pic: pic["originalPath"])

    # Return overlapping pairs for the comparison function to process (0+1, 1+2, 2+3, ...)
    return [{"duplicateId": i + 1, "assets": (assets[i], assets[i + 1])} for i in range(len(assets) - 1)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stack Immich duplicates with identical filenames (ignoring extension).")

    # Require either --stack or --dry-run
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stack", action="store_true", help="Find duplicates with identical filenames and stack them.")
    group.add_argument("--dry-run", action="store_true", help="Only print duplicates, do not stack them.")

    parser.add_argument("--all-albums", action="store_true", help="Process all assets in all albums.")
    parser.add_argument("--album", action="append", type=str, help="Process all assets in specific album(s) by ID.")

    parser.add_argument('--verbose', '-v', action='count', default=0, help='Increase verbosity')

    args = parser.parse_args()

    IMMICH_URL, API_KEY = load_config()

    if args.album:
        duplicates = []
        for album_id in args.album:
            duplicates += get_assets_in_album(IMMICH_URL, API_KEY, album_id)
    elif args.all_albums:
        duplicates = []
        for album_id in get_all_album_ids(IMMICH_URL, API_KEY):
            duplicates += get_assets_in_album(IMMICH_URL, API_KEY, album_id)
    else:
        duplicates = get_duplicates(IMMICH_URL, API_KEY)

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
