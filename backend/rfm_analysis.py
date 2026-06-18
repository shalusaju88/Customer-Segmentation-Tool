"""
Step 1: Data Collection & Cleaning → RFM Score Calculation
===========================================================
Uses the UCI "Online Retail" dataset (UK-based online store, 2010-2011).
Source: https://archive.ics.uci.edu/ml/datasets/Online+Retail

Pipeline:
  1. Download the dataset (CSV mirror via GitHub)
  2. Inspect raw data
  3. Remove missing CustomerID rows
  4. Filter out cancelled orders (InvoiceNo starting with 'C')
  5. Remove invalid/negative quantities and prices
  6. Calculate RFM scores per unique CustomerID
  7. Save cleaned RFM table to rfm_scores.csv
"""

import os
import urllib.request
import pandas as pd
import datetime

# ─────────────────────────────────────────────────────────
# 1.  Download or extract the dataset
# ─────────────────────────────────────────────────────────
# Known working mirrors of the UCI Online Retail dataset
DATASET_URLS = [
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx",
    "https://raw.githubusercontent.com/jorisvandenbossche/pandas-tutorial/master/data/online_retail.csv",
    "https://raw.githubusercontent.com/BlueGranite/AI-in-a-Day/master/data/Online%20Retail.csv",
]
DATA_DIR     = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LOCAL_ZIP    = os.path.join(DATA_DIR, "online+retail.zip")
LOCAL_EXCEL  = os.path.join(DATA_DIR, "Online Retail.xlsx")
LOCAL_CSV    = os.path.join(DATA_DIR, "online_retail.csv")
FALLBACK_SAMPLE = os.path.join(DATA_DIR, "sample_customer_data.csv")


def acquire_dataset():
    """Acquire the dataset by checking local zip, excel, csv or downloading."""
    # 1. Check if excel file already exists or can be extracted
    if os.path.exists(LOCAL_EXCEL):
        print(f"[OK] Excel dataset already present: {LOCAL_EXCEL}")
        return LOCAL_EXCEL

    if os.path.exists(LOCAL_ZIP):
        try:
            print(f"[>>] Found zip file {LOCAL_ZIP}. Extracting...")
            import zipfile
            with zipfile.ZipFile(LOCAL_ZIP, 'r') as zip_ref:
                zip_ref.extractall(DATA_DIR)
            if os.path.exists(LOCAL_EXCEL):
                print(f"[OK] Extracted to: {LOCAL_EXCEL}")
                return LOCAL_EXCEL
        except Exception as e:
            print(f"[!!] Zip extraction failed: {e}")

    # 2. Check if local CSV already exists
    if os.path.exists(LOCAL_CSV):
        print(f"[OK] CSV dataset already present: {LOCAL_CSV}")
        return LOCAL_CSV

    # 3. Try downloading from URLs
    for url in DATASET_URLS:
        try:
            print(f"[>>] Downloading from:\n     {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            filename = "Online Retail.xlsx" if url.endswith(".xlsx") else "online_retail.csv"
            dest_path = os.path.join(os.path.dirname(__file__), filename)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                
            with open(dest_path, "wb") as f:
                f.write(data)
            print(f"[OK] Saved to: {dest_path}")
            return dest_path
        except Exception as e:
            print(f"[!!] Download failed for {url}: {e}")

    # 4. Fall back to sample data
    print(f"[NOTE] Could not acquire real UCI dataset.")
    print(f"       Using local sample data instead: {FALLBACK_SAMPLE}")
    return FALLBACK_SAMPLE


# ─────────────────────────────────────────────────────────
# 2.  Load & Inspect raw data
# ─────────────────────────────────────────────────────────
def load_and_inspect(filepath):
    print("\n" + "=" * 60)
    print("STEP 2: Load & Inspect Raw Data")
    print("=" * 60)

    # Check extension
    if filepath.endswith((".xlsx", ".xls")):
        print(f"[>>] Loading Excel file: {filepath} (This might take a moment)...")
        df = pd.read_excel(filepath, engine="openpyxl")
        print(f"[OK] Excel loaded successfully.")
    else:
        # Try UTF-8 first, fall back to latin-1
        df = None
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(filepath, encoding=enc)
                print(f"[OK] Loaded with encoding: {enc}")
                break
            except UnicodeDecodeError:
                continue
        if df is None:
            raise ValueError(f"Could not read CSV file {filepath} with supported encodings.")

    print(f"\nShape            : {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"Columns          : {list(df.columns)}")
    print(f"\nData types:\n{df.dtypes}")
    print(f"\nMissing values:\n{df.isnull().sum()}")
    print(f"\nSample rows:\n{df.head(3).to_string()}")

    return df


# ─────────────────────────────────────────────────────────
# 3-5. Clean data
# ─────────────────────────────────────────────────────────
def clean_data(df):
    print("\n" + "=" * 60)
    print("STEPS 3-5: Cleaning Data")
    print("=" * 60)

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    # Map common column variants → standard names
    col_map = {
        "customerid": ["customerid", "customer_id", "cust_id", "client_id"],
        "invoicedate": ["invoicedate", "invoice_date", "orderdate", "order_date",
                        "date", "transaction_date"],
        "invoiceno": ["invoiceno", "invoice_no", "invoice_number", "orderid",
                      "order_id", "transaction_id"],
        "quantity": ["quantity", "qty"],
        "unitprice": ["unitprice", "unit_price", "price", "amount"],
    }

    rename = {}
    for target, variants in col_map.items():
        for v in variants:
            if v in df.columns and target not in df.columns:
                rename[v] = target
                break
    if rename:
        df = df.rename(columns=rename)

    rows_start = len(df)
    print(f"\nRows before cleaning : {rows_start:,}")

    # ── Step 3a: Remove rows with missing CustomerID ──
    df = df[df["customerid"].notna()]
    df = df[df["customerid"].astype(str).str.strip() != ""]
    print(f"  After dropping null CustomerID : {len(df):,} rows  "
          f"(-{rows_start - len(df):,})")

    # ── Step 3b: Parse dates ──
    df["invoicedate"] = pd.to_datetime(df["invoicedate"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["invoicedate"])
    print(f"  After dropping unparseable dates: {len(df):,} rows  "
          f"(-{before - len(df):,})")

    # ── Step 4: Filter out cancelled orders (InvoiceNo starts with 'C') ──
    before = len(df)
    df = df[~df["invoiceno"].astype(str).str.startswith("C")]
    print(f"  After removing cancellations   : {len(df):,} rows  "
          f"(-{before - len(df):,})")

    # ── Step 5: Remove invalid quantities & prices ──
    df["quantity"]  = pd.to_numeric(df["quantity"],  errors="coerce")
    df["unitprice"] = pd.to_numeric(df["unitprice"], errors="coerce")
    df = df.dropna(subset=["quantity", "unitprice"])

    before = len(df)
    df = df[(df["quantity"] > 0) & (df["unitprice"] > 0)]
    print(f"  After removing qty/price <= 0  : {len(df):,} rows  "
          f"(-{before - len(df):,})")

    print(f"\nRows after all cleaning : {len(df):,}  "
          f"(removed {rows_start - len(df):,} total, "
          f"{(rows_start - len(df)) / rows_start * 100:.1f}%)")
    return df


# ─────────────────────────────────────────────────────────
# 6.  Calculate RFM scores
# ─────────────────────────────────────────────────────────
def calculate_rfm(df):
    print("\n" + "=" * 60)
    print("STEP 6: Calculate RFM Scores")
    print("=" * 60)

    # Revenue per line item
    df = df.copy()
    df["line_total"] = df["quantity"] * df["unitprice"]

    # Snapshot date = day after the latest invoice in the dataset
    snapshot_date = df["invoicedate"].max() + datetime.timedelta(days=1)
    print(f"\nSnapshot date (reference for Recency): {snapshot_date.date()}")

    rfm = df.groupby("customerid").agg(
        # Recency: days since last purchase
        recency=("invoicedate",   lambda x: (snapshot_date - x.max()).days),
        # Frequency: number of unique invoices
        frequency=("invoiceno",   "nunique"),
        # Monetary: total spend
        monetary=("line_total",   "sum"),
    ).reset_index()

    rfm["monetary"] = rfm["monetary"].round(2)

    print(f"\nUnique customers segmented: {len(rfm):,}")
    print(f"\nRFM statistics:")
    print(rfm[["recency", "frequency", "monetary"]].describe().round(2).to_string())

    print(f"\nTop 10 customers by Monetary value:")
    top10 = rfm.sort_values("monetary", ascending=False).head(10)
    print(top10[["customerid", "recency", "frequency", "monetary"]].to_string(index=False))

    print(f"\nMost recent 10 customers (lowest Recency):")
    recent10 = rfm.sort_values("recency").head(10)
    print(recent10[["customerid", "recency", "frequency", "monetary"]].to_string(index=False))

    return rfm


# ─────────────────────────────────────────────────────────
# 7.  Save results
# ─────────────────────────────────────────────────────────
def save_rfm(rfm):
    out_path = os.path.join(DATA_DIR, "rfm_scores.csv")
    rfm.to_csv(out_path, index=False)
    print(f"\n[OK] RFM scores saved to: {out_path}")
    print(f"     Columns: {list(rfm.columns)}")
    return out_path


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" Customer Segmentation - Step 1: RFM Analysis")
    print("=" * 60)

    filepath = acquire_dataset()
    df_raw   = load_and_inspect(filepath)
    df_clean = clean_data(df_raw)
    rfm      = calculate_rfm(df_clean)
    save_rfm(rfm)

    print("\n[DONE] RFM analysis complete. Upload rfm_scores.csv to the")
    print("       dashboard at http://localhost:5000 to run clustering.")
