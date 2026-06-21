"""Fetch the raw UCI dataset if it isn't already present locally.

GSD scope: thin convenience wrapper. The repo may already ship the .txt/.zip,
so this is idempotent and exits early when the data is already on disk.
"""
import os
import urllib.request
import zipfile

URL = "https://archive.ics.uci.edu/static/public/235/individual+household+electric+power+consumption.zip"
ZIP_PATH = "individual+household+electric+power+consumption.zip"
TXT_PATH = "household_power_consumption.txt"


def main() -> None:
    if os.path.exists(TXT_PATH):
        print(f"{TXT_PATH} already present — nothing to do.")
        return
    if not os.path.exists(ZIP_PATH):
        print(f"Downloading {URL} ...")
        urllib.request.urlretrieve(URL, ZIP_PATH)
    print(f"Unzipping {ZIP_PATH} ...")
    with zipfile.ZipFile(ZIP_PATH) as z:
        z.extractall(".")
    print(f"Ready: {TXT_PATH}")


if __name__ == "__main__":
    main()
