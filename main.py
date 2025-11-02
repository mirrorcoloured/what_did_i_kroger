# %%
"""
Kroger appears to attempt to block automated access to their site

Things to try:
* update chrome and chromedriver to newest versions
* update userAgent string
* launch chrome, launch webdriver, paste url into chrome, paste url into webdriver, paste user/pass into chrome, paste user/pass into webdriver, click login chrome (rejects), click login webdriver (works)?


https://forum.vivaldi.net/topic/73500/kroger-website-login-not-working/9

They have an API, but not for customer orders
https://developer.kroger.com/reference/
"""
import csv
import datetime
import math
import random

# %% imports
# import os
import time

import dateutil
import undetected_chromedriver as uc

# from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from credentials import userpass

username, password = userpass()

# %% pretend to be a human
# useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
# options = webdriver.ChromeOptions()
# options.add_argument("start-maximized")
# options.add_experimental_option("excludeSwitches", ["enable-automation"])
# options.add_experimental_option("useAutomationExtension", False)
# # options.add_argument("--disable-blink-features=AutomationControlled")
# chrome_install = ChromeDriverManager().install()
# chromedriver_path = os.path.join(os.path.dirname(chrome_install), "chromedriver.exe")
# driver = webdriver.Chrome(options=options, service=Service(chromedriver_path))
# driver.execute_script(
#     "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
# )
# driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": useragent})

# %%
driver = uc.Chrome(headless=False, use_subprocess=False)

# %% define urls
# scrape_url = "https://www.kingsoopers.com/mypurchases"
# auth_url = "https://www.kingsoopers.com/signin"
scrape_url = "https://www.kroger.com/mypurchases"
auth_url = "https://www.kroger.com/signin"


# %% spoofing functions
def human_input(element, payload, low=0.05, high=0.2):
    element.click()
    for character in payload:
        time.sleep(random.uniform(low, high))
        element.send_keys(character)


# TODO more randomization like this

# %% sign in
driver.get(auth_url)
human_input(driver.find_element(By.ID, "signInName"), username)
human_input(driver.find_element(By.ID, "password"), password)
driver.find_element(By.ID, "continue").click()

# %% scrape purchase links
start_date = datetime.date(2018, 1, 1)
end_date = datetime.date.today()
start_date_string = start_date.strftime("%Y%m%d")
end_date_string = end_date.strftime("%Y%m%d")

driver.get(scrape_url)
time.sleep(1)  # last page element not loading?
last_page = int(driver.find_elements(By.CLASS_NAME, "kds-Pagination-link")[-1].text)
purchase_links = []
past_date = False
for page_number in range(1, last_page + 1):
    driver.get(f"https://www.kroger.com/mypurchases?tab=purchases&page={page_number}")
    time.sleep(20)
    cards = driver.find_elements(By.CLASS_NAME, "PO-NonPendingPurchase")
    for card in cards:
        date = card.find_element(By.XPATH, ".//a/div[1]/div[1]/div/span").text
        dt = dateutil.parser.parse(date).date()
        if start_date <= dt <= end_date:
            link = card.find_element(By.CLASS_NAME, "kds-Link").get_attribute("href")
            purchase_links.append(link)
        elif dt < end_date:
            past_date = True
            break
    if past_date:
        break

# %% cache links to file
with open(f"{start_date_string}-{end_date_string}_purchase_links.csv", "w") as f:
    f.write("\n".join(purchase_links))

# %% load from cache
with open(f"{start_date_string}-{end_date_string}_purchase_links.csv", "r") as f:
    purchase_links = f.read().split("\n")

# %%
orders = []
order_items = []
# %%
# for i, link in enumerate(reversed(purchase_links)):
for i, link in enumerate(purchase_links):
    if i < 34:
        continue
    print(f"order {i} of {len(purchase_links)}")

    # driver.get(link)
    page_number = math.floor(i / 10) + 1
    driver.get(f"https://www.kroger.com/mypurchases?tab=purchases&page={page_number}")
    time.sleep(random.random() * 5)  # TODO wait for loading element to disappear?
    href = "/" + "/".join(link.split("/")[3:])
    order_link = driver.find_element(By.XPATH, f"//a[@href = '{href}']")
    order_link.click()

    time.sleep(10 + random.random() * 5)  # TODO wait for loading element to disappear?

    # date = driver.find_element(By.XPATH, "//span[contains(text(),'Order date:')]").text
    # date = date.split(": ")[1]
    # date = driver.find_elements(By.XPATH, "//h2")[1].text
    # date = date[date.find(" ")+1:]
    date = link[52:62]

    # order_number_span = driver.find_element(
    #     By.XPATH, "//span[contains(text(),'Order Number:')]"
    # )
    # order_number = order_number_span.find_element(
    #     By.XPATH, "./following-sibling::span"
    # ).text

    order_number = link.split("/")[-1]

    # location = driver.find_elements(By.XPATH, "//main/div/span")[1].get_attribute('innerHTML').replace("<br>", " ")
    location = driver.find_elements(
        By.XPATH,
        "//div[contains(@class, 'PurchaseDetailLoaded-container')]/div/div/div/span",
    )[0].text

    # loyalty = driver.find_element(By.XPATH, "//*[contains(text(), 'Loyalty Card')]").get_attribute('innerHTML').split("ending in ")[1]

    orders.append({"ordernumber": order_number, "date": date, "address": location})

    items = driver.find_elements(By.CLASS_NAME, "PH-ProductCard-container")
    for item in items:
        item_data = {"ordernumber": order_number}
        item_data["date"] = date
        item_data["address"] = location
        item_data["name"] = item.find_element(By.XPATH, ".//*[contains(@class, 'PH-ProductCard-item-description')]").text
        item_data["total_price"] = item.find_element(By.XPATH, ".//mark[contains(@class, 'kds-Price-promotional')]").text.replace("\n", "")

        try:
            item_data["size"] = item.find_element(
                By.XPATH,
                ".//*[contains(@class, 'PH-ProductCard-item-description-size')]",
            ).text
        except NoSuchElementException as e:
            pass

        try:
            quantity_price = item.find_element(By.XPATH, ".//data/following-sibling::span").text
            item_data["quantity"] = quantity_price.split(" x ")[0]
            item_data["unit_price"] = quantity_price.split(" x ")[1].replace("/each", "")
        except NoSuchElementException as e:
            pass

        try:
            item_data["original_price"] = item.find_element(By.XPATH, ".//s[contains(@class, 'kds-Price-original')]").text
        except NoSuchElementException as e:
            pass

        try:
            item_data["link"] = item.find_element(By.XPATH, ".//a[contains(@class, 'kds-Link')][1]").get_attribute("href")
        except NoSuchElementException as e:
            pass

        order_items.append(item_data)


# %%
def list_of_dicts_to_csv(lod, filename):
    headers = []
    for row in lod:
        for key in row.keys():
            if key not in headers:
                headers.append(key)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        for row in lod:
            values = [row.get(h, "") for h in headers]
            writer.writerow(values)


# list_of_dicts_to_csv(orders, f"orders.csv")
list_of_dicts_to_csv(order_items, f"{start_date_string}-{end_date_string}_items.csv")

# %%
