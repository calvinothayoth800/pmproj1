# Dataset notes (Phase 01)

After building the cache:

```powershell
cd zomato-ai-recommendation
python scripts/build_cache.py
```

Inspect distributions locally:

```python
import pandas as pd
from pathlib import Path

df = pd.read_parquet(Path("data/processed/restaurants.parquet"))
print(df["city"].value_counts().head(30))
print(df["cuisines"].str.split("|").explode().value_counts().head(40))
```

Use the printed city/cuisine lists to populate Streamlit dropdowns (Phase 04).

### Phase 01 output columns

| Column | Description |
|--------|-------------|
| `restaurant_id` | Stable row id after dedupe |
| `name`, `city`, `location` | Listing identity |
| `cuisines` | Pipe-separated lowercase tokens |
| `rating` | Parsed 0–5 or missing |
| `votes` | Review votes |
| `cost_for_two` | INR approx for two |
| `budget_tier` | `low` / `medium` / `high` / `unknown` |
| `listed_in_type`, `rest_type`, `online_order`, `book_table`, `dish_liked` | Signals for filtering |

Excluded from cache: free-text blobs (`reviews_list`, full `menu_item`, raw URLs).
