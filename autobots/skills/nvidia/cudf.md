# cuDF GPU DataFrames

## Basic Operations
```python
import cudf
import pandas as pd

# Read data on GPU
df = cudf.read_csv("data.csv")

# Standard pandas API
filtered = df[df["column"] > 100]
grouped = df.groupby("category").agg({"value": "sum"})
sorted_df = df.sort_values("timestamp")
```

## GPU-Accelerated ETL
```python
# Filter + transform on GPU
result = (
    df
    .query("amount > 1000")
    .assign(category=lambda x: x["category"].str.lower())
    .groupby("category")
    .agg({"amount": "sum", "count": "mean"})
    .sort_values("amount", ascending=False)
)
```

## Performance Comparison
```python
# pandas (CPU)
import pandas as pd
pdf = pd.read_csv("large.csv")  # 10GB file
result = pdf.groupby("col").sum()  # 45 seconds

# cuDF (GPU)
gdf = cudf.read_csv("large.csv")  # 10GB file
result = gdf.groupby("col").sum()  # 0.3 seconds
```

## Migration from pandas
```python
# Replace import
# import pandas as pd
import cudf as pd

# Replace read_csv
# pd.read_csv → cudf.read_csv
# pd.read_parquet → cudf.read_parquet

# Most pandas API works identically
# Check: https://rapids.ai/api/cudf/stable/
```

## Interop
```python
# cuDF ↔ pandas
pdf = gdf.to_pandas()  # GPU → CPU
gdf = cudf.from_pandas(pdf)  # CPU → GPU

# cuDF ↔ Dask
import dask_cudf
dd = dask_cudf.read_csv("data/*.csv")
```
