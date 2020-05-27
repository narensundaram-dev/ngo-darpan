import logging
import argparse
import time
import configparser
from datetime import datetime as dt

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC


__author__ = "Narendran G"
__maintainer__ = "Narendran G"
__contact__ = "+91-8678910063"
__email__ = "narensundaram007@gmail.com"
__status__ = "Development"

log = logging.getLogger(__file__.split('/')[-1])


def config_logger(args):
    """
    This method is used to configure the logging format.
    :param args: script argument as `ArgumentParser instance`.
    :return: None
    """
    log_level = logging.INFO if args.log_level and args.log_level == 'INFO' else logging.DEBUG
    log.setLevel(log_level)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(name)s:%(lineno)d - %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)


class NGOScraper(object):

    def __init__(self, chrome, url, conf):
        self.chrome = chrome
        self.url = url
        self.conf = conf

    @classmethod
    def get_members(cls, soup):
        members = {}
        table = soup.find("table", attrs={"id": "member_table"})
        for i, e in enumerate(table.tbody):
            if i == 0: continue
            if i == 4: break
            k1, k2 = f"Name{i}", f"Designation{i}"
            members[k1], members[k2] = e.contents[0].get_text(), e.contents[1].get_text()
        return members

    @classmethod
    def get_info(cls, soup):
        info = {
            "ID": soup.find("span", attrs={"id": "UniqueID"}).get_text(),
            "Name": soup.find("span", attrs={"id": "ngo_name_title"}).get_text(),
            "Address": soup.find("td", attrs={"id": "address"}).get_text(),
            "City": soup.find("td", attrs={"id": "city"}).get_text(),
            "State": soup.find("td", attrs={"id": "state_p_ngo"}).get_text(),
            "Telephone": soup.find("td", attrs={"id": "phone_n"}).get_text(),
            "Mobile": soup.find("td", attrs={"id": "mobile_n"}).get_text(),
            "Website": soup.find("td", attrs={"id": "ngo_web_url"}).get_text(),
            "Email": soup.find("td", attrs={"id": "email_n"}).get_text(),
            "Key Issues": soup.find("td", attrs={"id": "key_issues"}).get_text(),
        }
        members = cls.get_members(soup)
        info.update(members)
        return info

    def get(self):
        self.chrome.get(self.url)

        try:
            WebDriverWait(self.chrome, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'Tax')))
        except (TimeoutException, Exception) as err:
            log.error("Error: {}".format(err))
            log.error("Loading the page takes too much time. Exiting...")
            exit(1)

        table = self.chrome.find_element_by_css_selector("table.Tax")

        data = []
        for idx, row in enumerate(table.find_elements_by_xpath(".//tr")):
            if idx == 0: continue

            link = row.find_element_by_tag_name("a")
            link.click()
            time.sleep(int(self.conf["WAIT_TIME_PER_NGO"]))  # Find a better way (like polling)

            html = self.chrome.page_source
            soup = BeautifulSoup(html, "html.parser")
            info = self.get_info(soup)
            data.append(info)
            log.debug("Fetched info: {}".format(info))

            self.chrome.find_elements_by_xpath('//span[@aria-hidden="true"]')[1].click()
            self.chrome.implicitly_wait(1)  # Find a better way (like polling)

        return data


class NGOManager(object):

    output_xlsx = "output.xlsx"
    site_url = "https://ngodarpan.gov.in/index.php/home/statewise_ngo/6919/7/{}?"
    bs_parser = "html.parser"

    def __init__(self, args, conf):
        self.args = args
        self.conf = conf
        self.data = []
        self.chrome = webdriver.Chrome(conf["CHROME_DRIVER_PATH"])
        self.last_successful_scrape = -1

    @classmethod
    def setup(cls):
        pass

    def get_last_page_no(self):
        self.chrome.get(NGOManager.site_url.format(1))
        try:
            WebDriverWait(self.chrome, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'pagination')))
        except (TimeoutException, Exception) as err:
            log.error("Error: {}".format(err))
            log.error("Loading the page takes too much time. Exiting...")
            exit(1)

        html = self.chrome.page_source
        soup = BeautifulSoup(html, NGOManager.bs_parser)
        last_page_no = int(list(soup.find("ul", attrs={"class": "pagination"}).children
                                )[-1].contents[0].attrs['data-ci-pagination-page'])
        log.info("Identified last page no: {}".format(last_page_no))
        return last_page_no

    def read(self):
        last_page_no = self.get_last_page_no()
        try:
            if int(self.conf["END_PAGE"]) >= 0:
                log.info("Taking END_PAGE as a input from conf file. Overriding the actual last page.")
                if int(self.conf["START_PAGE"]) > int(self.conf["END_PAGE"]):
                    log.error("START_PAGE should be lesser than END_PAGE. Please configure conf file properly!")
                    exit(1)

                last_page_no = int(self.conf["END_PAGE"])
            for page in range(int(self.conf["START_PAGE"]), last_page_no+1):
                # if page == 2: break
                url = NGOManager.site_url.format(page)
                log.info("Getting info from: {}".format(url))
                scraper = NGOScraper(self.chrome, url, self.conf)
                data = scraper.get()
                self.data.extend(data)
                self.last_successful_scrape = page
        except Exception as err:
            log.error("Some error happened: {}".format(err))
        finally:
            return self

    def save(self):
        df = pd.DataFrame(self.data)
        df.to_excel(NGOManager.output_xlsx, index=False)
        log.info("Fetched data has been stored in {} file".format(NGOManager.output_xlsx))

    @classmethod
    def cleanup(cls):
        pass


def get_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-log-level', '--log_level', type=str, choices=("INFO", "DEBUG"),
                            default="INFO", help='Where do you want to post the info?')
    return arg_parser.parse_args()


def get_conf():
    conf = configparser.ConfigParser()
    conf.read("conf.ini")
    return conf["CONFIG"]


def main():
    args = get_args()
    config_logger(args)
    conf = get_conf()

    start = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script starts at: {}".format(start))
    NGOManager.setup()

    manager = NGOManager(args, conf)
    manager.read().save()

    NGOManager.cleanup()
    end = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Last successful page extract: {}".format(manager.last_successful_scrape))
    log.info("Script ends at: {}".format(end))


if __name__ == '__main__':
    main()
