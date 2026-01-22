# %%
import re
from datetime import datetime

import pandas as pd
import plotly.express as px

order_df = pd.read_csv("data/2023-11-07_2026-01-17_orders.csv")
item_df = pd.read_csv("data/2023-11-07_2026-01-17_items.csv", dtype={"upc": str})

df = pd.merge(item_df, order_df, on="order_number")

# %%
order_df["spend"] = order_df.apply(lambda row: float(row["total_price"][1:]), axis=1)

df["spend"] = df.apply(lambda row: float(row["paid"][1:]), axis=1)
df["t"] = df.apply(lambda row: datetime.strptime(row["date"], "%Y-%m-%d"), axis=1)
df["year"] = df.apply(lambda row: row["t"].year, axis=1)
df["month"] = df.apply(lambda row: row["t"].month, axis=1)
df["day"] = df.apply(lambda row: row["t"].day, axis=1)

# fix types
# TODO extract from quantity matching "[\d.]+", "[\d.]+ lbs", "[\d.]+ gal"
df["quantity_lbs"] = df["quantity"].apply(lambda x: float(re.findall(r"([\d.]+) lbs", str(x))[0]) if "lbs" in str(x) else None)
df["quantity_gal"] = df["quantity"].apply(lambda x: float(re.findall(r"([\d.]+) gal", str(x))[0]) if "gal" in str(x) else None)
df["quantity_count"] = df["quantity"].apply(lambda x: float(re.findall(r"([\d.]+)", str(x))[0]) if "lbs" not in str(x) and "gal" not in str(x) else None)

# add clean columns
df["paid_$"] = df["paid"].apply(lambda x: float(re.findall(r"\$(\d+\.\d+)", str(x))[0]) if pd.notnull(x) else None)
df["$_per_count"] = df["paid_$"] / df["quantity_count"]
df["$_per_lbm"] = df["sizing"].apply(lambda x: float(re.findall(r"\$(\d+\.\d+)/lb", str(x))[0]) if str(x).endswith("/lb") else None)

# %%
gdf = df.groupby("name").agg({"spend": "sum"})
gdf.sort_values("spend", ascending=False, inplace=True)
print(gdf)
print("Total spend:", gdf["spend"].sum())

# %%
orders_by_loc = order_df.groupby(["location"]).agg({"spend": "sum", "order_number": "count"})
orders_by_loc["price_per_order"] = orders_by_loc["spend"] / orders_by_loc["order_number"]

# %%
df[df["name"].str.contains("Ice Cream")]["spend"].sum()

# %%
# bar graph of spend by month
monthly_spend = df.groupby(["year", "month"]).agg({"spend": "sum"}).reset_index()
monthly_spend["date"] = monthly_spend.apply(lambda row: datetime(int(row["year"]), int(row["month"]), 1), axis=1)
fig = px.bar(monthly_spend, x="date", y="spend", title="Monthly Spend Over Time")
fig.show()

# %%
# line graph of daily spend moving average
daily_spend = df.groupby(["year", "month", "day"]).agg({"spend": "sum"}).reset_index()
daily_spend["date"] = daily_spend.apply(lambda row: datetime(int(row["year"]), int(row["month"]), int(row["day"])), axis=1)
daily_spend = daily_spend.sort_values("date")
daily_spend["moving_avg"] = daily_spend["spend"].rolling(window=14).mean()
fig = px.line(daily_spend, x="date", y="moving_avg", title="14-Visit Moving Average of Daily Spend")
fig.show()

# %%
# for each unique item, count how many times it was bought, and show a bar chart of how many items were bought each number of times
repeat_buys = df.groupby("name").agg({"order_number": "nunique"}).reset_index().sort_values("order_number", ascending=False)
repeat_buys_count = repeat_buys.groupby("order_number").agg({"name": "count"}).reset_index()
fig = px.bar(
    repeat_buys_count,
    x="order_number",
    y="name",
    title="Number of Unique Items Bought by Number of Repeat Purchases",
    labels={"order_number": "Number of Repeat Purchases", "name": "Number of Unique Items"},
)
fig.show()

# %% spending on price per pound items over time
px.line(
    df[df.price_per_lbm.notnull()],
    x="t",
    y="$_per_lbm",
    color="name",
    markers=True,
    height=1000,
    labels={"t": "Date", "value": "Amount ($ / lbm)", "name": "Item"},
)

# %% price of bell peppers over time
pepper_colors = {
    "Fresh Large Green Bell Pepper": "#2ca02c",
    "Fresh Red Hothouse Bell Pepper": "#d62728",
    "Fresh Yellow Bell Pepper": "#ffdf00",
    "Fresh Orange Bell Pepper": "#ff7f0e",
}
px.line(
    df[df.name.isin(pepper_colors.keys())],
    x="t",
    y="$_per_count",
    color="name",
    color_discrete_map=pepper_colors,
    markers=True,
    height=600,
    labels={"t": "Date", "$_per_count": "Amount ($ / count)", "name": "Item"},
)

# %%
