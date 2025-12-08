# src/forexfactory/scraper.py

import time
import re
import logging
from datetime import datetime, timedelta

import pandas as pd
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
    InvalidSessionIdException,
)

from urllib3.exceptions import ReadTimeoutError, MaxRetryError

from .csv_util import (
    ensure_csv_header,
    read_existing_data,
    write_data_to_csv,
    merge_new_data,
)
from .detail_parser import parse_detail_table, detail_data_to_string

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# 🔥 On garde UNIQUEMENT ces impacts
# --------------------------------------------------------------------
ALLOWED_IMPACTS = ["High Impact Expected", "Medium Impact Expected"]


# --------------------------------------------------------------------
# Helper : créer un driver Chrome UC
# --------------------------------------------------------------------
def _launch_driver():
    """
    Lance un nouveau Chrome undetected_chromedriver avec une taille de fenêtre fixe.
    """
    logger.info("Starting new undetected_chromedriver instance...")
    driver = uc.Chrome()
    driver.set_window_size(1400, 1000)
    return driver


# --------------------------------------------------------------------
# Parsing d'une journée
# --------------------------------------------------------------------
def parse_calendar_day(
    driver,
    the_date: datetime,
    scrape_details: bool = False,
    existing_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Scrape une seule journée et renvoie un DataFrame filtré sur:
      - High Impact Expected
      - Medium Impact Expected
    Colonnes : DateTime, Currency, Impact, Event, Actual, Forecast, Previous, Detail
    """

    date_str = the_date.strftime("%b%d.%Y").lower()
    url = f"https://www.forexfactory.com/calendar?day={date_str}"

    logger.info(f"Scraping URL: {url}")

    # Sécurité : timeout de chargement de page
    driver.set_page_load_timeout(180)
    driver.get(url)

    try:
        WebDriverWait(driver, 25).until(
            EC.visibility_of_element_located(
                (By.XPATH, '//table[contains(@class,"calendar__table")]')
            )
        )
    except TimeoutException:
        logger.warning(f"Calendar did not load for {the_date.date()}")
        return pd.DataFrame(
            columns=[
                "DateTime",
                "Currency",
                "Impact",
                "Event",
                "Actual",
                "Forecast",
                "Previous",
                "Detail",
            ]
        )

    rows = driver.find_elements(
        By.XPATH, '//tr[contains(@class,"calendar__row")]'
    )
    data_list: list[dict] = []
    current_day = the_date

    for row in rows:
        try:
            row_class = row.get_attribute("class") or ""
        except StaleElementReferenceException:
            continue

        # On ignore les séparateurs, lignes sans event, etc.
        if "day-breaker" in row_class or "no-event" in row_class:
            continue

        try:
            time_el = row.find_element(
                By.XPATH, './/td[contains(@class,"calendar__time")]'
            )
            currency_el = row.find_element(
                By.XPATH, './/td[contains(@class,"calendar__currency")]'
            )
            impact_el = row.find_element(
                By.XPATH, './/td[contains(@class,"calendar__impact")]'
            )
            event_el = row.find_element(
                By.XPATH, './/td[contains(@class,"calendar__event")]'
            )
            actual_el = row.find_element(
                By.XPATH, './/td[contains(@class,"calendar__actual")]'
            )
            forecast_el = row.find_element(
                By.XPATH, './/td[contains(@class,"calendar__forecast")]'
            )
            previous_el = row.find_element(
                By.XPATH, './/td[contains(@class,"calendar__previous")]'
            )
        except NoSuchElementException:
            continue
        except StaleElementReferenceException:
            continue

        # Texte brut
        time_text = time_el.text.strip()
        currency_text = currency_el.text.strip()

        # Impact via tooltip
        try:
            impact_span = impact_el.find_element(By.XPATH, ".//span")
            impact_text = impact_span.get_attribute("title") or ""
        except Exception:
            impact_text = impact_el.text.strip()

        # ----------------------------------------------------------------
        # FILTRAGE : on garde uniquement High & Medium
        # ----------------------------------------------------------------
        if impact_text not in ALLOWED_IMPACTS:
            continue

        event_text = event_el.text.strip()
        actual_text = actual_el.text.strip()
        forecast_text = forecast_el.text.strip()
        previous_text = previous_el.text.strip()

        # ----------------------------------------------------------------
        # Conversion heure → datetime
        # ----------------------------------------------------------------
        event_dt = current_day
        t = time_text.lower()

        if "day" in t:
            # "All Day" ou similaire
            event_dt = event_dt.replace(hour=23, minute=59, second=59)
        else:
            m = re.match(r"(\d{1,2}):(\d{2})(am|pm)", t)
            if m:
                hh = int(m.group(1))
                mm = int(m.group(2))
                ap = m.group(3)
                if ap == "pm" and hh < 12:
                    hh += 12
                if ap == "am" and hh == 12:
                    hh = 0
                event_dt = event_dt.replace(hour=hh, minute=mm, second=0)

        # ----------------------------------------------------------------
        # Gestion des détails
        # ----------------------------------------------------------------
        detail_str = ""
        if scrape_details:
            # 1) On regarde d'abord dans le CSV existant
            if existing_df is not None and not existing_df.empty:
                try:
                    matched = existing_df[
                        (existing_df["DateTime"] == event_dt.isoformat())
                        & (existing_df["Currency"].str.strip() == currency_text)
                        & (existing_df["Event"].str.strip() == event_text)
                    ]
                    if not matched.empty:
                        existing_detail = matched.iloc[0].get("Detail", "")
                        if isinstance(existing_detail, str) and existing_detail.strip():
                            detail_str = existing_detail.strip()
                except Exception:
                    # On ne bloque pas si problème sur existing_df
                    pass

            # 2) Si aucun détail trouvé → on tente de les récupérer
            if not detail_str:
                try:
                    detail_link = row.find_element(
                        By.XPATH,
                        './/td[contains(@class,"calendar__detail")]/a',
                    )
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior:'instant',block:'center'});",
                        detail_link,
                    )
                    time.sleep(0.5)
                    detail_link.click()

                    WebDriverWait(driver, 7).until(
                        EC.visibility_of_element_located(
                            (
                                By.XPATH,
                                '//tr[contains(@class,"calendar__details--detail")]',
                            )
                        )
                    )
                    detail_data = parse_detail_table(driver)
                    detail_str = detail_data_to_string(detail_data)
                except Exception:
                    # Si erreur sur les détails, on laisse vide
                    detail_str = ""
                finally:
                    # Fermer la ligne de détail si possible
                    try:
                        close_btn = row.find_element(
                            By.XPATH, './/a[@title="Close Detail"]'
                        )
                        close_btn.click()
                    except Exception:
                        pass

        data_list.append(
            {
                "DateTime": event_dt.isoformat(),
                "Currency": currency_text,
                "Impact": impact_text,
                "Event": event_text,
                "Actual": actual_text,
                "Forecast": forecast_text,
                "Previous": previous_text,
                "Detail": detail_str,
            }
        )

    return pd.DataFrame(data_list)


# --------------------------------------------------------------------
# Wrapper pour scrapper une journée
# --------------------------------------------------------------------
def scrape_day(
    driver,
    the_date: datetime,
    existing_df: pd.DataFrame,
    scrape_details: bool = False,
) -> pd.DataFrame:
    return parse_calendar_day(
        driver, the_date, scrape_details=scrape_details, existing_df=existing_df
    )


# --------------------------------------------------------------------
# Boucle principale sur la plage de dates
# --------------------------------------------------------------------
def scrape_range_pandas(
    from_date: datetime,
    to_date: datetime,
    output_csv: str,
    tzname: str = "Africa/Casablanca",
    scrape_details: bool = False,
):
    """
    Scrape de from_date à to_date (inclus) avec :
      - Filtrage High/Medium impact
      - Driver UC qui se relance en cas de crash
      - Écriture CSV incrémentale
    """

    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)

    driver = _launch_driver()
    total_new = 0
    current = from_date
    day_count = (to_date - from_date).days + 1

    logger.info(
        f"Scraping from {from_date.date()} to {to_date.date()} "
        f"({day_count} days) into {output_csv}"
    )

    try:
        while current <= to_date:
            logger.info(f"Day: {current.strftime('%Y-%m-%d')}")

            # On autorise plusieurs tentatives pour cette journée
            attempts = 0
            max_attempts = 3
            df_new = pd.DataFrame()

            while attempts < max_attempts:
                try:
                    df_new = scrape_day(
                        driver,
                        current,
                        existing_df,
                        scrape_details=scrape_details,
                    )
                    break  # succès → on sort de la boucle de retry

                except (
                    InvalidSessionIdException,
                    WebDriverException,
                    ReadTimeoutError,
                    MaxRetryError,
                ) as e:
                    attempts += 1
                    logger.error(
                        f"Driver error on {current.date()} "
                        f"(attempt {attempts}/{max_attempts}): {e}"
                    )
                    # On tente de relancer le driver
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(2)
                    driver = _launch_driver()
                    # On réessaie la même journée
                    continue

                except Exception as e:
                    # Erreur inattendue : on log et on passe au jour suivant
                    logger.exception(
                        f"Unexpected error on {current.date()}, skipping this day."
                    )
                    df_new = pd.DataFrame()
                    break

            if attempts == max_attempts and df_new.empty:
                logger.warning(
                    f"Failed to scrape {current.date()} after {max_attempts} attempts, skipping."
                )
                current += timedelta(days=1)
                continue

            # Merge et écriture CSV
            if not df_new.empty:
                merged = merge_new_data(existing_df, df_new)
                new_rows = len(merged) - len(existing_df)
                if new_rows > 0:
                    logger.info(f"Added {new_rows} rows")
                existing_df = merged
                write_data_to_csv(existing_df, output_csv)
                total_new += new_rows

            # Jour suivant
            current += timedelta(days=1)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # Sauvegarde finale de sécurité
    write_data_to_csv(existing_df, output_csv)
    logger.info(f"FINISHED. Total new/updated rows: {total_new}")
