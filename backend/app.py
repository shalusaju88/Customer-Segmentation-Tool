"""
Customer Segmentation Tool - Flask Backend
Handles CSV upload, data cleaning, RFM scoring, K-Means clustering, and cluster profiling.
Supports both raw transaction CSVs and pre-aggregated customer-level CSVs.
"""

import io
import datetime
import traceback

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)


# ──────────────────────────────────────────────
# Serve frontend files
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")


# ──────────────────────────────────────────────
# Main segmentation endpoint
# ──────────────────────────────────────────────
@app.route("/api/segment", methods=["POST"])
def segment():
    try:
        # ── 1. Read inputs ──
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded. Please attach a dataset file."}), 400

        file = request.files["file"]
        n_clusters = int(request.form.get("clusters", 4))
        n_clusters = max(2, min(n_clusters, 8))

        # ── 2. Parse File (CSV, Excel, or Zip) ──
        filename = file.filename.lower() if file.filename else ""
        raw_df = None
        file_bytes = file.read()

        if filename.endswith(".zip"):
            try:
                import zipfile
                zip_buffer = io.BytesIO(file_bytes)
                with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                    # Find first CSV or Excel file in ZIP
                    names = zip_ref.namelist()
                    data_file = None
                    for name in names:
                        if name.lower().endswith((".csv", ".xlsx", ".xls")) and not name.split('/')[-1].startswith("."):
                            data_file = name
                            break
                    if not data_file:
                        return jsonify({"error": "No valid CSV or Excel file found inside the uploaded ZIP archive."}), 400
                    
                    inner_bytes = zip_ref.read(data_file)
                    inner_name = data_file.lower()
                    if inner_name.endswith((".xlsx", ".xls")):
                        raw_df = pd.read_excel(io.BytesIO(inner_bytes), engine="openpyxl")
                    else:
                        for enc in ["utf-8", "latin-1", "cp1252"]:
                            try:
                                raw_df = pd.read_csv(io.StringIO(inner_bytes.decode(enc)))
                                break
                            except Exception:
                                continue
            except Exception as e:
                return jsonify({"error": f"Failed to extract or parse ZIP archive: {str(e)}"}), 400

        elif filename.endswith((".xlsx", ".xls")):
            try:
                raw_df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
            except Exception as e:
                return jsonify({"error": f"Failed to parse Excel file: {str(e)}"}), 400

        else:
            # Fall back to CSV parsing
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    raw_df = pd.read_csv(io.StringIO(file_bytes.decode(enc)))
                    break
                except Exception:
                    continue

        if raw_df is None:
            return jsonify({"error": "Could not parse the file. Please ensure it is a valid CSV, Excel, or ZIP archive."}), 400

        # Normalize column names (strip whitespace, lowercase)
        raw_df.columns = raw_df.columns.str.strip().str.lower()

        # ── 3. Detect CSV format ──
        # We support two formats:
        #   A) Raw transactions  – one row per purchase (InvoiceNo, Quantity, UnitPrice, etc.)
        #   B) Pre-aggregated   – one row per customer (TotalOrders, TotalSpent, LastPurchaseDate)

        PRE_AGG_FREQUENCY_VARIANTS = [
            "totalorders", "total_orders", "frequency", "order_count",
            "num_orders", "numberoforders", "purchases",
        ]
        PRE_AGG_MONETARY_VARIANTS = [
            "totalspent_inr", "totalspent", "total_spent", "totalamount",
            "total_amount", "monetary", "revenue", "total_revenue",
            "lifetimevalue", "ltv",
        ]
        PRE_AGG_RECENCY_VARIANTS = [
            "lastpurchasedate", "last_purchase_date", "lastorderdate",
            "last_order_date", "last_seen", "last_transaction_date",
            "recency",
        ]
        PRE_AGG_CUSTOMER_VARIANTS = [
            "customerid", "customer_id", "cust_id", "client_id",
            "customername", "customer_name", "name",
        ]

        def find_col(cols, variants):
            for v in variants:
                if v in cols:
                    return v
            return None

        freq_col = find_col(raw_df.columns, PRE_AGG_FREQUENCY_VARIANTS)
        mon_col  = find_col(raw_df.columns, PRE_AGG_MONETARY_VARIANTS)
        rec_col  = find_col(raw_df.columns, PRE_AGG_RECENCY_VARIANTS)
        cid_col  = find_col(raw_df.columns, PRE_AGG_CUSTOMER_VARIANTS)

        is_pre_aggregated = bool(freq_col and mon_col and cid_col)

        # ────────────────────────────────────────
        # Path A: Pre-aggregated customer CSV
        # ────────────────────────────────────────
        if is_pre_aggregated:
            df = raw_df.copy()
            original_rows = len(df)

            # Drop rows with missing customer ID
            df = df[df[cid_col].notna() & (df[cid_col].astype(str).str.strip() != "")]

            rfm = pd.DataFrame()
            rfm["customerid"] = df[cid_col].astype(str).values

            # Frequency
            rfm["frequency"] = pd.to_numeric(df[freq_col].values, errors="coerce")
            rfm["frequency"] = rfm["frequency"].fillna(1)

            # Monetary
            rfm["monetary"] = pd.to_numeric(df[mon_col].values, errors="coerce")
            rfm["monetary"] = rfm["monetary"].fillna(0).round(2)

            # Recency
            if rec_col:
                col_data = df[rec_col]
                numeric_try = pd.to_numeric(col_data, errors="coerce")
                if numeric_try.notna().sum() > len(df) * 0.5:
                    # Column is already numeric days
                    rfm["recency"] = numeric_try.fillna(numeric_try.median()).round(0).astype(int).values
                else:
                    # Try parsing as a date
                    date_try = pd.to_datetime(col_data, errors="coerce")
                    if date_try.notna().sum() > len(df) * 0.5:
                        snapshot = date_try.max() + datetime.timedelta(days=1)
                        days = (snapshot - date_try).dt.days
                        rfm["recency"] = days.fillna(days.median()).astype(int).values
                    else:
                        rfm["recency"] = 30
            else:
                rfm["recency"] = 30

            cleaned_rows = len(rfm)
            removed_rows = original_rows - cleaned_rows
            snapshot_date_str = datetime.date.today().strftime("%Y-%m-%d")

        # ────────────────────────────────────────
        # Path B: Raw transaction CSV
        # ────────────────────────────────────────
        else:
            col_map = {
                "customerid": ["customerid", "customer_id", "cust_id", "client_id"],
                "invoicedate": ["invoicedate", "invoice_date", "orderdate", "order_date", "date", "transaction_date"],
                "invoiceno":   ["invoiceno", "invoice_no", "invoice_number", "orderid", "order_id", "transaction_id"],
                "quantity":    ["quantity", "qty"],
                "unitprice":   ["unitprice", "unit_price", "price", "amount"],
            }

            resolved = {}
            for target, variants in col_map.items():
                for v in variants:
                    if v in raw_df.columns:
                        resolved[target] = v
                        break

            missing = [k for k in col_map if k not in resolved]
            if missing:
                return jsonify({
                    "error": (
                        "Could not recognise the CSV format. "
                        "For raw transactions, required columns: InvoiceNo, InvoiceDate, Quantity, UnitPrice, CustomerID. "
                        "For pre-aggregated data, required columns: CustomerID, TotalOrders (or Frequency), TotalSpent (or Monetary). "
                        f"Found columns: {', '.join(raw_df.columns.tolist())}"
                    )
                }), 400

            df = raw_df.rename(columns={v: k for k, v in resolved.items()})
            original_rows = len(df)

            # Clean
            df = df[df["customerid"].notna() & (df["customerid"].astype(str).str.strip() != "")]
            df["invoicedate"] = pd.to_datetime(df["invoicedate"], errors="coerce")
            df = df.dropna(subset=["invoicedate"])
            df["quantity"]  = pd.to_numeric(df["quantity"],  errors="coerce")
            df["unitprice"] = pd.to_numeric(df["unitprice"], errors="coerce")
            df = df.dropna(subset=["quantity", "unitprice"])
            df = df[~df["invoiceno"].astype(str).str.startswith("C")]
            df = df[df["quantity"]  > 0]
            df = df[df["unitprice"] > 0]

            cleaned_rows = len(df)
            removed_rows = original_rows - cleaned_rows

            if cleaned_rows == 0:
                return jsonify({"error": "No valid transactions remain after cleaning. Please check your data."}), 400

            # Compute RFM
            df["totalamount"] = df["quantity"] * df["unitprice"]
            snapshot_date = df["invoicedate"].max() + datetime.timedelta(days=1)
            snapshot_date_str = snapshot_date.strftime("%Y-%m-%d")

            rfm = df.groupby("customerid").agg(
                recency=("invoicedate",  lambda x: (snapshot_date - x.max()).days),
                frequency=("invoiceno",  "nunique"),
                monetary=("totalamount", "sum"),
            ).reset_index()
            rfm["monetary"] = rfm["monetary"].round(2)

        # ── Validate minimum rows ──
        if len(rfm) < n_clusters:
            return jsonify({
                "error": (
                    f"Only {len(rfm)} customers found after cleaning, but {n_clusters} clusters requested. "
                    "Please reduce the number of clusters or provide more data."
                )
            }), 400

        # ── Scale & Cluster ──
        features = rfm[["recency", "frequency", "monetary"]].values
        
        # Apply symmetric log transform to handle right skewness and massive outliers safely
        log_features = np.zeros_like(features)
        for col_idx in range(3):
            col_data = features[:, col_idx]
            log_features[:, col_idx] = np.sign(col_data) * np.log1p(np.abs(col_data))
            
        scaler   = StandardScaler()
        scaled   = scaler.fit_transform(log_features)

        # ── Elbow Method: compute inertia for K = 2..8 ──
        max_k = min(8, len(rfm) - 1)
        elbow_data = []
        for k in range(2, max_k + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
            km.fit(scaled)
            elbow_data.append({"k": k, "inertia": round(float(km.inertia_), 4)})

        # ── Apply chosen K ──
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
        rfm["cluster"] = kmeans.fit_predict(scaled)

        # ── PCA for 2D visualization ──
        pca    = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(scaled)
        rfm["pca_x"] = coords[:, 0].round(4)
        rfm["pca_y"] = coords[:, 1].round(4)

        # ── Normalized RFM coords for 3D scatter ──
        rfm["rfm_x"] = scaled[:, 0].round(4)   # Recency (normalized)
        rfm["rfm_y"] = scaled[:, 1].round(4)   # Frequency (normalized)
        rfm["rfm_z"] = scaled[:, 2].round(4)   # Monetary (normalized)

        # ── Profile clusters ──
        cluster_summary = rfm.groupby("cluster").agg(
            count=("customerid",  "count"),
            avg_recency=("recency",   "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary",  "mean"),
            min_recency=("recency",   "min"),
            max_recency=("recency",   "max"),
            min_frequency=("frequency", "min"),
            max_frequency=("frequency", "max"),
            min_monetary=("monetary",  "min"),
            max_monetary=("monetary",  "max"),
        ).reset_index()

        cluster_summary = cluster_summary.sort_values("cluster").reset_index(drop=True)
        labels = _auto_label_clusters(cluster_summary)

        profiles = []
        for _, row in cluster_summary.iterrows():
            cid = int(row["cluster"])
            label_info = labels[cid]
            profiles.append({
                "cluster":       cid,
                "name":          label_info["name"],
                "color":         label_info["color"],
                "icon":          label_info["icon"],
                "description":   label_info["description"],
                "action":        label_info["action"],
                "count":         int(row["count"]),
                "pct":           round(row["count"] / len(rfm) * 100, 1),
                "avg_recency":   round(row["avg_recency"],   1),
                "avg_frequency": round(row["avg_frequency"], 1),
                "avg_monetary":  round(row["avg_monetary"],  2),
            })

        # ── Build customer list with segment labels ──
        cluster_name_map = {p["cluster"]: p["name"] for p in profiles}
        rfm["segment"] = rfm["cluster"].map(cluster_name_map)

        customers = rfm.to_dict(orient="records")
        for c in customers:
            for k, v in c.items():
                if isinstance(v, np.integer):
                    c[k] = int(v)
                elif isinstance(v, np.floating):
                    c[k] = float(v)

        return jsonify({
            "success": True,
            "stats": {
                "original_rows":   original_rows,
                "cleaned_rows":    cleaned_rows,
                "removed_rows":    removed_rows,
                "total_customers": len(rfm),
                "clusters":        n_clusters,
                "snapshot_date":   snapshot_date_str,
                "format":          "pre-aggregated" if is_pre_aggregated else "raw-transactions",
            },
            "elbow":     elbow_data,
            "profiles":  profiles,
            "customers": customers,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Cluster auto-labelling
# ──────────────────────────────────────────────
def _auto_label_clusters(summary_df):
    """
    Assign meaningful labels based on relative RFM rankings.
    Lower composite score = better cluster (recent, frequent, high-spend).
    """
    df = summary_df.copy()
    df["r_rank"] = df["avg_recency"].rank(ascending=True)
    df["f_rank"] = df["avg_frequency"].rank(ascending=False)
    df["m_rank"] = df["avg_monetary"].rank(ascending=False)
    df["score"]  = df["r_rank"] + df["f_rank"] + df["m_rank"]
    df = df.sort_values("score")

    archetypes = [
        {
            "name": "Champions",
            "color": "#f59e0b", "icon": "trophy",
            "description": "Your best customers. Bought recently, buy often, and spend the most.",
            "action": "Reward them with exclusive perks. Engage them as brand ambassadors.",
        },
        {
            "name": "Loyal Customers",
            "color": "#8b5cf6", "icon": "gem",
            "description": "Consistent buyers with strong frequency and solid spending.",
            "action": "Upsell premium products. Offer loyalty programs and early access.",
        },
        {
            "name": "Potential Loyalists",
            "color": "#10b981", "icon": "seedling",
            "description": "Recent customers with growing engagement. High conversion potential.",
            "action": "Nurture with onboarding sequences and personalized recommendations.",
        },
        {
            "name": "Active Regulars",
            "color": "#3b82f6", "icon": "bolt",
            "description": "Moderately active customers with average engagement across metrics.",
            "action": "Increase engagement with targeted campaigns and bundle offers.",
        },
        {
            "name": "At Risk",
            "color": "#ef4444", "icon": "alert",
            "description": "Previously good customers whose activity has declined noticeably.",
            "action": "Reactivate with win-back campaigns, special discounts, and surveys.",
        },
        {
            "name": "Hibernating",
            "color": "#6b7280", "icon": "moon",
            "description": "Inactive customers who haven't purchased in a long time.",
            "action": "Send re-engagement emails. Consider removing from active campaigns.",
        },
        {
            "name": "New Visitors",
            "color": "#06b6d4", "icon": "sparkle",
            "description": "Brand new customers with very few transactions so far.",
            "action": "Welcome series, first-purchase incentives, and educational content.",
        },
        {
            "name": "Declining",
            "color": "#f97316", "icon": "trending-down",
            "description": "Customers showing reduced activity and spend over time.",
            "action": "Intervene early with satisfaction surveys and retention offers.",
        },
    ]

    labels = {}
    used = set()
    for _, row in df.iterrows():
        cid = int(row["cluster"])
        for arch in archetypes:
            if arch["name"] not in used:
                labels[cid] = arch
                used.add(arch["name"])
                break
        else:
            labels[cid] = {
                "name": f"Segment {cid + 1}",
                "color": "#9ca3af", "icon": "users",
                "description": "A customer segment.",
                "action": "Analyze further to determine best strategy.",
            }

    return labels


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("[*] Customer Segmentation Tool running at http://localhost:5000")
    app.run(debug=True, port=5000)
