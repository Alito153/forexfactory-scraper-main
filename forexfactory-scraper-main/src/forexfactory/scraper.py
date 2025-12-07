# src/forexfactory/scraper.py

import time
import re
import logging
import pandas as pd
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)
import undetected_chromedriver as uc

from .csv_util import ensure_csv_header, read_existing_data, write_data_to_csv, merge_new_data
from .detail_parser import parse_detail_table, detail_data_to_string

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# 🔥 FILTRAGE IMPACT : seuls ces impacts sont gardés
# --------------------------------------------------------------------
ALLOWED_IMPACTS = ["High Impact Expected", "Medium Impact Expected"]


def parse_calendar_day(driver, the_date: datetime, scrape_details=False, existing_df=None) -> pd.DataFrame:
    """
    Scrape data for a single day and return a DataFrame filtered to:
      - High Impact Expected
      - Medium Impact Expected
    """
    date_str = the_date.strftime('%b%d.%Y').lower()
    url = f"https://www.forexfactory.com/calendar?day={date_str}"

    logger.info(f"Scraping URL: {url}")
    driver.set_page_load_timeout(180)
    driver.get(url)

    try:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, '//table[contains(@class,"calendar__table")]'))
        )
    except TimeoutException:
        logger.warning(f"Calendar did not load for {the_date.date()}")
        return pd.DataFrame(columns=["DateTime","Currency","Impact","Event","Actual","Forecast","Previous","Detail"])

    rows = driver.find_elements(By.XPATH, '//tr[contains(@class,"calendar__row")]')
    data_list = []
    current_day = the_date

    for row in rows:

        # Ignore separators and blank rows
        row_class = row.get_attribute("class")
        if "day-breaker" in row_class or "no-event" in row_class:
            continue

        # Extract fields
        try:
            time_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__time")]')
            currency_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__currency")]')
            impact_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__impact")]')
            event_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__event")]')
            actual_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__actual")]')
            forecast_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__forecast")]')
            previous_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__previous")]')
        except NoSuchElementException:
            continue

        # Text extraction
        time_text = time_el.text.strip()
        currency_text = currency_el.text.strip()

        # Impact (using tooltip)
        try:
            impact_span = impact_el.find_element(By.XPATH, './/span')
            impact_text = impact_span.get_attribute("title") or ""
        except:
            impact_text = impact_el.text.strip()

        # --------------------------------------------------------------------
        # FILTRAGE: skip si Low / None / vide
        # --------------------------------------------------------------------
        if impact_text not in ALLOWED_IMPACTS:
            continue

        event_text = event_el.text.strip()
        actual_text = actual_el.text.strip()
        forecast_text = forecast_el.text.strip()
        previous_text = previous_el.text.strip()

        # Convert time to datetime
        event_dt = current_day
        t = time_text.lower()

        if "day" in t:
            event_dt = event_dt.replace(hour=23, minute=59, second=59)
        elif re.match(r'\d{1,2}:\d{2}(am|pm)', t):
            m = re.match(r'(\d{1,2}):(\d{2})(am|pm)', t)
            hh = int(m.group(1))
            mm = int(m.group(2))
            ap = m.group(3)
            if ap == "pm" and hh < 12:
                hh += 12
            if ap == "am" and hh == 12:
                hh = 0
            event_dt = event_dt.replace(hour=hh, minute=mm, second=0)

        # Key for checking existing details
        detail_str = ""
        if scrape_details:
            if existing_df is not None:
                match = existing_df[
                    (existing_df["DateTime"] == event_dt.isoformat()) &
                    (existing_df["Currency"].str.strip() == currency_text) &
                    (existing_df["Event"].str.strip() == event_text)
                ]
                if not match.empty and pd.notnull(match.iloc[0]["Detail"]):
                    detail_str = match.iloc[0]["Detail"]

            if not detail_str:
                try:
                    btn = row.find_element(By.XPATH, './/td[contains(@class,"calendar__detail")]/a')
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    btn.click()
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, '//tr[contains(@class,"calendar__details--detail")]')
                        )
                    )
                    detail_data = parse_detail_table(driver)
                    detail_str = detail_data_to_string(detail_data)
                except Exception:
                    detail_str = ""
                finally:
                    try:
                        close_btn = row.find_element(By.XPATH, './/a[@title="Close Detail"]')
                        close_btn.click()
                    except:
                        pass

        data_list.append({
            "DateTime": event_dt.isoformat(),
            "Currency": currency_text,
            "Impact": impact_text,
            "Event": event_text,
            "Actual": actual_text,
            "Forecast": forecast_text,
            "Previous": previous_text,
            "Detail": detail_str
        })

    return pd.DataFrame(data_list)


def scrape_day(driver, the_date, existing_df, scrape_details=False):
    return parse_calendar_day(driver, the_date, scrape_details=scrape_details, existing_df=existing_df)


def scrape_range_pandas(from_date, to_date, output_csv, tzname="Asia/Tehran", scrape_details=False):
    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)

    driver = uc.Chrome()
    driver.set_window_size(1400, 1000)

    total_new = 0
    day_count = (to_date - from_date).days + 1
    logger.info(f"Scraping {day_count} days: {from_date.date()} → {to_date.date()}")

    try:
        current = from_date
        while current <= to_date:

            logger.info(f"Day: {current.strftime('%Y-%m-%d')}")

            df_new = scrape_day(driver, current, existing_df, scrape_details=scrape_details)

            if not df_new.empty:
                merged = merge_new_data(existing_df, df_new)
                new_rows = len(merged) - len(existing_df)
                if new_rows > 0:
                    logger.info(f"Added {new_rows} rows")
                existing_df = merged
                write_data_to_csv(existing_df, output_csv)
                total_new += new_rows

            current += timedelta(days=1)

    finally:
        try:
            driver.quit()
        except:
            pass

    write_data_to_csv(existing_df, output_csv)
    logger.info(f"Finished. New rows added: {total_new}")
