#!/usr/bin/env python3

import argparse
import os
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import earthaccess
from earthaccess.exceptions import LoginAttemptFailure, LoginStrategyUnavailable

DEFAULT_DATASET_VERSION = "2"
DEFAULT_THREADS = 1
OUTPUT_DIR_TEMPLATE = "{level}/{product}/{mode}/{year}/{month}/{day}"  # Relative to --output_dir. Date fields refer to the granule sensing start.

def granule_subdirectory(filename):
    """
    Given the filename of a S5P granule, return the corresponding directory tree relative to --output_dir specified through argparse
    """

    # Accept paths and URLs as well as filenames; NASA links may use lowercase.
    basename = Path(unquote(urlsplit(str(filename)).path)).name.upper()

    # Extract the relevant fields (level, product, etc.) using a regex
    match = re.match(
        r"^S5P_(?P<mode>[A-Z0-9]+)_+(?P<level>L[12]B?)_+"
        r"(?P<product>[A-Z0-9_]+?)_+(?P<start>\d{8}T\d{6})_",
        basename,
    )

    if match is None:
        raise ValueError(f"Cannot infer output structure from filename: {filename}")

    # extract `start`, which refers to the sensing start time of the granule
    # e.g.: an orbit that begins on 2019-05-01 but reaches into 2019-05-02 will be stored under 2019/05/01.
    start = datetime.strptime(match["start"], "%Y%m%dT%H%M%S")

    relative_output_dir = Path(OUTPUT_DIR_TEMPLATE.format(
        level=match["level"],
        product=match["product"],
        mode=match["mode"],
        year=start.strftime("%Y"),
        month=start.strftime("%m"),
        day=start.strftime("%d"),
    ))

    return relative_output_dir


def main(argv=None):
    """
    Parse CLI arguments and download granules without interactive prompts.
    """

    parser = argparse.ArgumentParser(description="Download TROPOMI granules from NASA Earthdata.")
    parser.add_argument("product", help="Earthdata product short name (e.g. 'S5P_L2__NO2____HiR')")
    parser.add_argument("--date", "-d", type=date.fromisoformat, help="Single day to download (YYYY-MM-DD); use instead of --start_date and --end_date")
    parser.add_argument("--start_date", "-s", type=date.fromisoformat, help="First day to include (YYYY-MM-DD)")
    parser.add_argument("--end_date", "-e", type=date.fromisoformat, help="Last day to include (YYYY-MM-DD)")
    parser.add_argument("--dataset_version", "-v", default=DEFAULT_DATASET_VERSION, help="Dataset version (default: %(default)s)")
    parser.add_argument("--output_dir", "-o", type=Path, required=True, help="Root directory for the inferred product/date directory structure")
    parser.add_argument("--threads", type=int, default=DEFAULT_THREADS, help="Number of download threads (default: %(default)s)")
    args = parser.parse_args(argv)
    args.output_dir = args.output_dir.expanduser().resolve()

    # User must specify either `date` or a combination of `start_date` and `end_date`
    if args.date is not None:
        if args.start_date is not None or args.end_date is not None:
            parser.error("--date cannot be combined with --start_date or --end_date")
        args.start_date = args.end_date = args.date

    # If 'date' is specified, neither 'start_date' nor 'end_date' must be specified
    elif args.start_date is None or args.end_date is None:
        parser.error("provide either --date or both --start_date and --end_date")

    # 'start_date' must be on or before 'end_date'
    if args.start_date > args.end_date:
        parser.error("start_date must be on or before end_date")

    # 'threads' must be at least 1
    if args.threads < 1:
        parser.error("threads must be at least 1")

    print("Welcome to TROPOMI download (MPIC)")

    # Notify user about output location
    print(f"Downloaded data will be stored under {args.output_dir}")

    # Read Earthdata credentials from NETRC or the default ~/.netrc.
    netrc_path = Path(os.environ.get("NETRC", "~/.netrc")).expanduser()
    if not netrc_path.is_file():
        raise SystemExit(
            f"Earthdata credentials file not found: {netrc_path}\n"
            "Create ~/.netrc with an entry for machine urs.earthdata.nasa.gov, "
            "including login and password, or set the environment variable `NETRC` to an existing credentials file.\n"
            "For more information, see the NASA credential setup instructions: "
            "https://urs.earthdata.nasa.gov/documentation/for_users/data_access/curl_and_wget "
            "or https://github.com/LeonKuhn/tropomi_downloader_mpic#authentication"
        )

    # prepare error message in case authentication fails
    authentication_error = (
        "Earthdata authentication failed. Check the credentials for "
        f"urs.earthdata.nasa.gov in {netrc_path}.\n"
        "For more information, see the NASA credential setup instructions: "
        "https://urs.earthdata.nasa.gov/documentation/for_users/data_access/curl_and_wget "
        "or https://github.com/LeonKuhn/tropomi_downloader_mpic#authentication"
    )
    try:
        auth = earthaccess.login(strategy="netrc", persist=False)
    except (LoginAttemptFailure, LoginStrategyUnavailable):
        raise SystemExit(authentication_error)
    if not auth.authenticated:
        raise SystemExit(authentication_error)

    # Fetch granules from Earthdata
    granules = earthaccess.search_data(
        short_name=args.product,
        version=args.dataset_version,
        cloud_hosted=True,
        temporal=(args.start_date, args.end_date),
    )

    if not granules:
        print("No matching granules found.")
        return

    # In order to achieve our desired output directory tree, we must call earthacess.download once per output directory
    # (this is defined by `OUTPUT_DIR_TEMPLATE` above)
    granules_by_directory = defaultdict(list)
    for granule in granules:

        # extract the URL stored within the granule
        urls = granule.data_links()
        if len(urls) != 1:
            raise ValueError(f"Expected one data URL per granule, received {len(urls)}: {urls}")

        # extract the filename from the URL
        filename = urlsplit(urls[0]).path
        if not filename.lower().endswith(".nc"):
            raise ValueError(f"Expected a NetCDF (.nc) data URL, received: {urls[0]}")

        subdirectory = granule_subdirectory(filename)
        directory = args.output_dir / subdirectory
        granules_by_directory[directory].append(granule)

    # start download
    for directory, directory_granules in granules_by_directory.items():
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {len(directory_granules)} granules to {directory}")
        earthaccess.download(
            directory_granules,
            local_path=directory,
            threads=args.threads,
            show_progress=True,
        )


if __name__ == "__main__":
    main()
