# %%
import textwrap
from datetime import datetime

import pandas as pd
import plotly.express as px
from ollama import chat, embed
from pydantic import BaseModel
from sklearn.cluster import dbscan

# %%
order_df = pd.read_csv("data/2023-11-07_2025-10-27_orders.csv")
item_df = pd.read_csv("data/2023-11-07_2025-10-27_items.csv", dtype={"upc": str})

df = pd.merge(item_df, order_df, on="order_number")

item_names = df.name.unique().tolist()

# %%
vectors = embed("nomic-embed-text", item_names)
vector_map = {item_names[i]: vectors.embeddings[i] for i in range(len(item_names))}

dbs = dbscan(vectors.embeddings)
cluster_map = {item_names[i]: int(dbs[1][i]) for i in range(len(item_names))}

clusters = {}
for item, cluster in cluster_map.items():
    if cluster not in clusters:
        clusters[cluster] = []
    else:
        clusters[cluster].append(item)


# %%
class ItemClassification(BaseModel):
    description: str
    non_food: bool
    breakfast_food: bool
    snack: bool


def classify_food(food_name: str):
    prompt = textwrap.dedent(
        """Please classify this purchased item according to this schema:
        {schema}
        This is the item you must classify:
        {food_name}"""
    )
    response = chat(
        messages=[
            {
                "role": "user",
                "content": prompt.format(
                    schema=ItemClassification.model_json_schema(),
                    food_name=food_name,
                ),
            }
        ],
        model="llama3.2:1b",
        format=ItemClassification.model_json_schema(),
    )

    content = response["message"]["content"]
    stats = ItemClassification.model_validate_json(content)
    return stats


# %%
