## Requirements:
- `Python 3.6.8`

## Setup:
- Install chrome-driver(for your chrome version) from https://chromedriver.chromium.org/downloads
- Extract the downloaded zip to C://chromedriver.exe
- Add the path to `conf.ini` under variable `CHROME_DRIVER_PATH`
- `pip install -r requirements.txt`

## How to run:
- `python ngo.py -log-level [INFO | DEBUG]`
- Data will be stored in `output.xlsx`
