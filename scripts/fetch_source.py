"""Download one complete, pinned OpenSkeleton release; verify every MD5."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RECORD = "22833546"
API = f"https://zenodo.org/api/records/{RECORD}"
SUPPORT = ("Faces.mat", "Metadata.mat", "README.txt", "EXAMPLE_GetData.m", "PCAData.m")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "md5").hexdigest()


def fetch(geometry: bool) -> None:
    raw = ROOT / "data" / "raw" / RECORD
    raw.mkdir(parents=True, exist_ok=True)
    provenance = ROOT / "sources"
    provenance.mkdir(exist_ok=True)
    snapshot = provenance / f"openskeleton-{RECORD}.json"
    if snapshot.exists():
        record = json.loads(snapshot.read_text())
    else:
        with urllib.request.urlopen(API, timeout=60) as response:
            record = json.load(response)
        if record["metadata"]["license"]["id"] != "cc-by-4.0":
            raise ValueError("Unexpected source license; review before downloading")
        snapshot.write_text(json.dumps(record, indent=2) + "\n")
    names = ("NM_combined.mat",) if geometry else SUPPORT
    files = {item["key"]: item for item in record["files"]}
    for name in names:
        item = files[name]
        expected = item["checksum"].removeprefix("md5:")
        target = raw / name
        if target.exists() and target.stat().st_size == item["size"] and digest(target) == expected:
            print(f"Verified cached {name}", flush=True)
            continue
        temporary = target.with_suffix(target.suffix + ".part")
        print(f"Downloading {name}: {item['size']:,} bytes", flush=True)
        url = f"https://zenodo.org/records/{RECORD}/files/{name}?download=1"
        request = urllib.request.Request(url, headers={"User-Agent": "TSB-Anatomy/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if temporary.stat().st_size != item["size"] or digest(temporary) != expected:
            raise ValueError(f"Integrity check failed: {name}; kept .part for inspection")
        temporary.replace(target)
        print(f"Verified {name}: md5:{expected}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", action="store_true", help="Download the 2.46 GB combined geometry instead of support files")
    fetch(parser.parse_args().geometry)
