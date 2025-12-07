# src/forexfactory/main.py

import sys
import os
import logging
import argparse
from datetime import datetime
from dateutil.tz import gettz

from .incremental import scrape_incremental

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Forex Factory Scraper")
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--csv', type=str, default="forex_factory_cache.csv")
    parser.add_argument('--tz', type=str, default="Asia/Tehran")
    parser.add_argument('--details', action='store_true')

    args = parser.parse_args()

    # ---------------------------------------------------------
    # 🔥 Avant de scraper: si le CSV existe → ON LE SUPPRIME
    # ---------------------------------------------------------
    if os.path.exists(args.csv):
        print(f"[INFO] Removing old CSV: {args.csv}")
        os.remove(args.csv)

    tz = gettz(args.tz)
    from_date = datetime.fromisoformat(args.start).replace(tzinfo=tz)
    to_date = datetime.fromisoformat(args.end).replace(tzinfo=tz)

    scrape_incremental(
        from_date,
        to_date,
        args.csv,
        tzname=args.tz,
        scrape_details=args.details
    )


if __name__ == "__main__":
    main()
