# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.common.by import By

# fp = webdriver.FirefoxProfile()
# opts = Options()
# # opts.set_headless()
# driver = webdriver.Firefox(options=opts, firefox_profile=fp)
# driver.implicitly_wait(10)

# import requests
# s = requests.Session()
# s.auth = (username, password)
# r = s.get(url)
# r = requests.get(url, auth=(username, password))

import time

from selenium import webdriver
from credentials import userpass
username, password = userpass()

driver = webdriver.Chrome()

# scrape_url = "https://www.kingsoopers.com/mypurchases"
scrape_url = "https://www.kroger.com/mypurchases"
# auth_url = "https://www.kingsoopers.com/signin"
auth_url = "https://www.kroger.com/signin"

driver.get(auth_url)
driver.find_element_by_id("SignIn-emailInput").send_keys(username)
driver.find_element_by_id("SignIn-passwordInput").send_keys(password)
driver.find_element_by_id("SignIn-submitButton").click()

driver.get(scrape_url)
purchase_links = []
for page_number in range(1, 27+1):
    driver.get(f"https://www.kroger.com/mypurchases?tab=purchases&page={page_number}")
    time.sleep(5)
    elements = [e for e in driver.find_elements_by_class_name("kds-Link") if e.get_attribute('href').find('/mypurchases/') > -1]
    for e in elements:
        purchase_links.append(e.get_attribute('href'))

with open('purchase_links.csv', 'w') as f:
    for link in purchase_links:
        f.write(f"{link}\n")

orders = []
order_items = []
for link in purchase_links:
    driver.get(link)
    time.sleep(5)
    order, date = driver.find_element_by_xpath("//main/div/span").get_attribute('innerHTML').split("<br>")
    order = order.split(" ")[1]
    date = date.split(": ")[1]
    location = driver.find_elements_by_xpath("//main/div/span")[1].get_attribute('innerHTML').replace("<br>", " ")

    # loyalty = driver.find_element_by_xpath("//*[contains(text(), 'Loyalty Card')]").get_attribute('innerHTML').split("ending in ")[1]

    orders.append([order, date, location])

    items = driver.find_elements_by_xpath("//a[contains(@href, '/item/')]")
    for i, item in enumerate(items):
        if i%2 == 0: continue
        text = remove_brackets(item.get_attribute('innerHTML'))
        if len(text) > 1:
            fulltext = remove_brackets(item.find_element_by_xpath("../../../..").get_attribute('innerHTML'))
            fulltext = remove_duplicates(fulltext, "|")
            order_items.append([order, fulltext])

with open('orders.csv', 'w') as f:
    for order in orders:
        line = ",".join([qualify(o, '"') for o in order])
        f.write(f'{line}\n')

with open('orders_items.csv', 'w') as f:
    for item in order_items:
        line = ",".join([qualify(o, '"') for i in item])
        f.write(f'{line}\n')

def qualify(string, qualifier='"'):
    if not (string[0] == qualifier and string[-1] == qualifier):
        return f"{qualifier}{string}{qualifier}"
    return string

def remove_brackets(s):
    while s.find("<") > -1 and s.find(">") > -1:
        left = s.find("<")
        right = s.find(">", left) + 1
        s = s[:left] + "|" + s[right:]
    return s

def remove_duplicates(s, dup):
    new_s = s[0]
    for i, c in enumerate(s):
        if i == 0: continue
        if not (c == dup and s[i - 1] == dup):
            new_s += c
    return new_s
