# %%
from datetime import datetime

import pandas as pd
import plotly.express as px

order_df = pd.read_csv("2023-11-07_2025-10-27_orders.csv")
item_df = pd.read_csv("2023-11-07_2025-10-27_items.csv", dtype={"upc": str})

df = pd.merge(item_df, order_df, on="order_number")

# %%
order_df["spend"] = order_df.apply(lambda row: float(row["total_price"][1:]), axis=1)

df["spend"] = df.apply(lambda row: float(row["paid"][1:]), axis=1)
df["t"] = df.apply(lambda row: datetime.strptime(row["date"], "%Y-%m-%d"), axis=1)
df["year"] = df.apply(lambda row: row["t"].year, axis=1)
df["month"] = df.apply(lambda row: row["t"].month, axis=1)
df["day"] = df.apply(lambda row: row["t"].day, axis=1)

# %%
px.pie(df, "name", "spend")
px.violin(df, "paid")

gdf = df.groupby("name").agg({"spend": "sum"})
gdf.sort_values("spend", ascending=False, inplace=True)
print(gdf)
print("Total spend:", gdf["spend"].sum())
px.pie(gdf, gdf.index, "spend")

# %%
orders_by_loc = order_df.groupby(["location"]).agg({"spend": "sum", "order_number": "count"})
orders_by_loc["price_per_order"] = orders_by_loc["spend"] / orders_by_loc["order_number"]

# %%
df[df["name"].str.contains("Ice Cream")]["spend"].sum()

# %%
