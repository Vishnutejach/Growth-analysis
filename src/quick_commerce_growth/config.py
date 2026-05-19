from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

LOCAL_DATA_PATH = RAW_DATA_DIR / "d2c_marketing_funnel_data.csv"
SOURCE_DATA_PATH = Path(os.getenv("D2C_FUNNEL_DATA_PATH", LOCAL_DATA_PATH))

FUNNEL_STAGES = [
    "visited_website",
    "viewed_product",
    "added_to_cart",
    "checkout_started",
    "purchase_completed",
]

DIMENSIONS = ["channel", "campaign_type", "device", "region", "user_type"]
