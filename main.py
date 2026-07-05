# %%
import asyncio
import datetime
import json
import os
import re
import random
import sys
import time

import lxml.html
import pandas as pd
import zendriver as zd

from credentials import userpass

# %%
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# %%
ROOT_URL = "https://www.kingsoopers.com"
# ROOT_URL = "https://www.kroger.com"
login_url = f"{ROOT_URL}/signin"
orders_url = f"{ROOT_URL}/mypurchases"

start_date = datetime.date(2018, 1, 1)
end_date = datetime.date.today()
start_date_string = start_date.strftime("%Y%m%d")
end_date_string = end_date.strftime("%Y%m%d")


# %%
async def login():
    browser = await zd.start()
    page = await browser.get(login_url)

    time.sleep(10 + random.randint(0, 5))

    # sign in
    username, password = userpass()
    email_input = await page.xpath("//input[@id='signInName']")
    email_input = email_input[0]
    await email_input.send_keys(username)

    time.sleep(random.random() * 2 + 1)

    password_input = await page.xpath("//input[@id='password']")
    password_input = password_input[0]
    await password_input.send_keys(password)

    time.sleep(random.random() * 2 + 1)

    remember_checkbox = await page.xpath("//input[@id='kr_remember_me_adi_true']")
    remember_checkbox = remember_checkbox[0]
    await remember_checkbox.click()

    time.sleep(random.random() * 2 + 1)

    sign_in_button = await page.xpath("//button[@id='continue']")
    sign_in_button = sign_in_button[0]
    await sign_in_button.click()

    time.sleep(10 + random.randint(0, 5))

    return browser


async def get_order_links(browser, past_order_links=[]):
    print("Checking for order page count")
    page = await browser.get(orders_url)
    time.sleep(10)
    # results = await page.xpath("//*[contains(@class, 'kds-Pagination-link')]")
    # last_page = int(results[-1].text)
    pagelinks = [r.get("href") for r in await page.xpath("//a[contains(@href, 'page')]") if r.get("href")]
    pages = [int(re.findall(r"page=(\d*)", x)[0]) for x in pagelinks]
    last_page = max(pages)
    print(f"Found {last_page} pages of orders")

    new_order_links = []
    for page_number in range(1, last_page + 1):
        print(f"Pulling order numbers from page {page_number}")
        page = await browser.get(f"{ROOT_URL}/mypurchases?tab=purchases&page={page_number}")

        sleep_time = 15 + random.randint(0, 10)
        print(f"Sleeping for {sleep_time} seconds to allow JS to load")
        time.sleep(sleep_time)

        links = await page.xpath("//a")
        detail_links = [link for link in links if "mypurchases/detail" in (link.get("href") if link.get("href") else "")]
        order_links = [link.get("href") for link in detail_links]

        for link in order_links:
            if link not in past_order_links:
                new_order_links.append(link)
            else:
                print("Found an order I've already seen, done!")
                return new_order_links

    return new_order_links


def text_parts(e) -> list[str]:
    """Gets the individual text elements that are children of an element"""
    lines = []
    for i in e.xpath(".//*"):
        content = i.text
        # content = i.text_content()
        if not content or len(content) == 0:
            continue
        lines.append(content)
    return lines


def get_order_filename(order_link: str, cache_dir: str) -> str:
    return os.path.join(cache_dir, order_link.replace("/", "-") + ".html")


def get_cached_html(order_link: str, cache_dir: str) -> str:
    """Get the cached html for an order, or return False if not cached"""
    os.makedirs(cache_dir, exist_ok=True)
    filename = get_order_filename(order_link, cache_dir)
    if os.path.exists(filename):
        print(f"Loading order {order_link} from cache")
        with open(filename, "r", encoding="utf-8") as f:
            page_html = f.read()
            return page_html
    return False


async def get_order_html(browser, order_link: str, cache_dir: str) -> str:
    """Fetch raw order html, or serve from cache if pulled before"""
    chtml = get_cached_html(order_link, cache_dir)
    if chtml:
        return chtml

    print(f"Scraping order {order_link}")
    page = await browser.get(f"{ROOT_URL}{order_link}")

    # wait for js to load content
    time.sleep(15 + random.randint(0, 10))

    page_html = await page.get_content()
    if "We're sorry but we were unable to retrieve your orders." in page_html:
        print(f"Error loading page, retrying... {order_link}")
        page_html = get_order_html(browser, order_link, cache_dir)

    filename = get_order_filename(order_link, cache_dir)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(page_html)

    return page_html


def parse_order_html(order_link: str, page_html: str) -> tuple[list[dict], list[dict]]:
    etree = lxml.html.fromstring(page_html)

    order_details = {}
    order_details["order_number"] = order_link.split("/")[-1]
    order_details["date"] = order_link.split("~")[2]

    # extract from top card
    purchase_details_div = etree.xpath("//*[contains(text(), 'Purchase Details')]/following-sibling::div")[0]

    # order_details["total_price"] = purchase_details_div.xpath("//span[contains(text(), 'Total')]/following-sibling::data")[0].text_content()

    # total_string = purchase_details_div.xpath("//span[contains(text(), 'Total')]")[0].text_content()
    # order_details["total_price"] = re.search(r"Total: \$(.*)", total_string)[1]

    order_details["total_price"] = re.findall(r".*Total\s?\$([\d\.]*).*", purchase_details_div.text_content())

    # order_details["total_savings"] = ...
    location_span = purchase_details_div.xpath("./div/div/div/div/span")[0]
    order_details["location"] = location_span.text_content()
    while location_span.xpath("./following-sibling::span"):
        location_span = location_span.xpath("./following-sibling::span")[0]
        order_details["location"] += "\n" + location_span.text_content()

    # extract from order summary
    order_summary_div = etree.xpath("//*[contains(text(), 'Order Summary')]/parent::div/parent::div")[0]

    # ensure order number matches
    # page_order_number = order_summary_div.xpath("./*[contains(text(), 'Order Number:')]/following-sibling::*")[0].text_content()
    # page_order_number = etree.xpath("//*[contains(text(), 'Order Number')]/following-sibling::*")[0].text_content()
    # assert order_details["order_number"] == page_order_number, f"Order number mismatch: {order_details['order_number']} != {page_order_number}"

    # pull other order summary info
    order_details["payment_item_total"] = order_summary_div.xpath(".//*[contains(text(), 'Item Total')]/following-sibling::span")[0].text_content()
    try:
        order_details["payment_item_sales"] = order_summary_div.xpath(".//*[contains(text(), 'Item Coupons/Sales')]/following-sibling::span")[0].text_content()
    except:
        ...
    try:
        order_details["payment_tax"] = order_summary_div.xpath(".//*[contains(text(), 'Tax')]/following-sibling::span")[0].text_content()
    except:
        ...
    order_details["payment_order_total"] = order_summary_div.xpath(".//*[text() = ' Total']/following-sibling::span")[0].text_content()
    order_details["payment_method"] = order_summary_div.xpath(".//*[contains(text(), 'Payment Method')]/following-sibling::div/span")[0].text_content()
    try:
        order_details["total_savings"] = order_summary_div.xpath(".//*[text() = 'Total Savings']/preceding-sibling::span")[0].text_content()
    except:
        order_details["total_savings"] = "$0"
        ...

    # extract from item details
    items = purchase_details_div.xpath(".//li")
    all_items = []
    for item in items:
        item_data = {"order_number": order_details["order_number"]}

        try:
            link = item.xpath(".//a/h3/parent::a")[0]
            item_data["name"] = link.text_content()
            item_data["upc"] = link.get("href").split("/")[-1]
            item_data["link"] = f'{ROOT_URL}{link.get("href")}'
        except:
            item_data["name"] = text_parts(item)[0]

        try:
            item_data["sizing"] = item.xpath(".//*[@data-testid = 'product-item-sizing']")[0].text_content()
        except Exception as e:
            ...
        item_data["quantity"] = item.xpath(".//*[contains(text(), 'Received')]/span")[0].text_content()
        item_data["paid"] = item.xpath(".//*[contains(text(), 'Paid')]/*")[0].text_content()
        if " discounted from " in item_data["paid"]:
            paid, full = item_data["paid"].split(" discounted from ")
            item_data["paid"] = paid
            item_data["original"] = full

        all_items.append(item_data)

    return order_details, all_items


# %%
async def scrape_order_data(cache_dir: str):
    browser = await login()

    print("Reading order links from file")
    with open("data/order_links.json", "r") as f:
        past_order_links = json.load(f)

    new_order_links = await get_order_links(browser, past_order_links)

    if len(new_order_links) == 0:
        print("No new orders found, exiting")
        await browser.stop()
        return

    # update which orders I've seen
    print("Saving order links to file")
    all_order_links = past_order_links + new_order_links
    with open("data/order_links.json", "w") as f:
        json.dump(all_order_links, f, indent=2)

    # fetch each order's html and cache results
    for order_link in all_order_links:
        await get_order_html(browser, order_link, cache_dir)

    await browser.stop()


def process_data(cache_dir: str):
    with open("data/order_links.json", "r") as f:
        all_order_links = json.load(f)

    # offline, extract content from html
    all_order_details = []
    all_item_details = []
    for order_link in all_order_links:
        try:
            page_html = get_cached_html(order_link, cache_dir)
            order_details, all_items = parse_order_html(order_link, page_html)
            all_order_details.append(order_details)
            all_item_details.extend(all_items)
        except Exception as e:
            print(f"Error with order_link `{order_link}`")
            raise e

    # populate dataframes and export
    order_df = pd.DataFrame(all_order_details)
    item_df = pd.DataFrame(all_item_details)

    date_range = f"{order_df.date.min()}_{order_df.date.max()}"
    print(f"Saving csvs for {date_range}")
    order_df.to_csv(f"data/{date_range}_orders.csv", index=False)
    item_df.to_csv(f"data/{date_range}_items.csv", index=False)


def troubleshoot():
    process_data(CACHE_DIR)

    import webbrowser

    order_link = "/mypurchases/detail/620~00082~2026-07-02~119~3761845"
    page_html = get_cached_html(order_link, CACHE_DIR)
    filename = get_order_filename(order_link, CACHE_DIR)
    webbrowser.open(filename)


if __name__ == "__main__":
    CACHE_DIR = "./data/orders"

    asyncio.run(scrape_order_data(CACHE_DIR))

    process_data(CACHE_DIR)

# %%
