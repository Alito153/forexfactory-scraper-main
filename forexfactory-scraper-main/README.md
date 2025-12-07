Voici ton **README mis à jour, propre, complet, optimisé pour Python 3.12**, avec toutes les étapes, les correctifs, les commandes PowerShell et les solutions aux erreurs Chrome/ChromeDriver.

Tu n’as rien à modifier : tu peux copier-coller directement.

---

# ✔️ README MIS À JOUR (VERSION PRO)

````markdown
# Forex Factory Scraper

A robust and flexible web scraper for [Forex Factory](https://www.forexfactory.com/) calendar events.  
Fully compatible with **Python 3.12+**, Selenium 4, and the patched version of *undetected-chromedriver*.

This tool collects, updates, and manages Forex Factory event data with incremental scraping, timezone support, and optional detailed event information.

---

# Download
Download pre-scraped CSV datasets from:  
https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar

---

# Table of Contents
- [Features](#features)
- [Installation](#installation)
  - [Special Notes for Python 3.12+](#special-notes-for-python-312)
- [Usage](#usage)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
  - [Python 3.12 Issues](#python-312-issues)
  - [Chrome / ChromeDriver Errors](#chrome--chromedriver-errors)
- [Contributing](#contributing)
- [License](#license)

---

# Features

- **Incremental scraping** (only new or updated events)
- **Optional detailed event data**
- **Custom date range selection**
- **Timezone support**
- **Automatic ChromeDriver patching via undetected-chromedriver**
- **pandas integration** for CSV merging and cleaning
- **Selenium error handling**
- **CLI-driven workflow**

---

# Installation

## Prerequisites

- **Python 3.7+**, fully tested up to **Python 3.12**
- **Google Chrome installed**

---

## Step-by-Step Installation

### 1. Clone the Repository

```powershell
git clone https://github.com/yourusername/forexfactory_scraper.git
cd forexfactory_scraper
````

### 2. Create and Activate Virtual Environment

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Upgrade pip

```powershell
pip install --upgrade pip
```

---

# ⚠️ Special Notes for Python 3.12+

Python 3.12 **removed `distutils`**, which breaks old versions of `undetected-chromedriver`.

To fix this, install the patched version:

```powershell
pip install git+https://github.com/QIN2DIM/undetected-chromedriver.git
```

This version:

* removes all `distutils` dependencies
* supports Chrome ≥ 120
* works perfectly with Selenium 4.27+

Then install other dependencies:

```powershell
pip install -r requirements.txt
```

Requirements:

```
selenium==4.27.1
pandas>=2.2.3
python-dateutil>=2.8.2
tzdata==2024.2
```

---

# Usage

Run the scraper from the project root:

```powershell
python -m src.forexfactory.main --start YYYY-MM-DD --end YYYY-MM-DD --csv output.csv --tz TIMEZONE [--details]
```

### Arguments:

| Argument    | Description                                     |
| ----------- | ----------------------------------------------- |
| `--start`   | Start date (`YYYY-MM-DD`)                       |
| `--end`     | End date (`YYYY-MM-DD`)                         |
| `--csv`     | Output CSV (default: `forex_factory_cache.csv`) |
| `--tz`      | Timezone (default: `Asia/Tehran`)               |
| `--details` | Scrape detailed event info                      |

---

# Examples

### 1. Scrape with details

```powershell
python -m src.forexfactory.main --start 2024-03-21 --end 2024-03-25 --csv data.csv --tz Africa/Casablanca --details
```

### 2. Scrape without details

```powershell
python -m src.forexfactory.main --start 2024-01-01 --end 2024-01-31 --csv january.csv --tz Europe/Paris
```

### 3. Large multi-year scrape

```powershell
python -m src.forexfactory.main --start 2010-01-01 --end 2025-12-31 --csv full.csv --tz Africa/Casablanca
```

---

# Troubleshooting

## Python 3.12 Issues

### 🔥 Error: `ModuleNotFoundError: No module named 'distutils'`

Cause: Python 3.12 removed distutils.
Fix: install patched undetected-chromedriver:

```powershell
pip uninstall -y undetected-chromedriver
pip install git+https://github.com/QIN2DIM/undetected-chromedriver.git
```

---

## Chrome / ChromeDriver Errors

### ❌ Error:

```
This version of ChromeDriver only supports Chrome version X  
Current browser version is Y
```

### ✔️ Fix: Update Chrome

Open:

```
chrome://settings/help
```

Chrome updates automatically to the newest version.

### ✔️ Fix: Delete old patched drivers

```powershell
Remove-Item -Recurse -Force "$env:APPDATA\undetected_chromedriver"
```

Then rerun your script.

---

### ❌ Error:

```
session not created: cannot connect to chrome at 127.0.0.1
```

### ✔️ Fix:

1. Close all Chrome windows
2. Kill zombie Chrome processes:

```powershell
taskkill /F /IM chrome.exe
taskkill /F /IM chromedriver.exe
```

3. Relaunch scraper.

---

### ❌ Error: “Could not reach Chrome”

Fix:

```powershell
chrome.exe --remote-debugging-port=0
```

---

### ❌ Selenium “DevToolsActivePort file doesn't exist”

Fix:

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Google\Chrome\User Data"
```

---

# Contributing

1. Fork the project
2. Create a feature branch
3. Commit changes
4. Push
5. Open a pull request

---

# License

This project is licensed under the MIT License.

---

**Disclaimer:**
This scraper is for educational and personal use only.
Check ForexFactory’s Terms of Service before automated data collection.

```
