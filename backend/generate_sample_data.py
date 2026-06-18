"""
Generate realistic sample customer transaction data for the Customer Segmentation Tool.
Creates a CSV with ~8000 transactions across ~500 customers over 12 months.
"""

import csv
import random
import datetime
import os

def generate_sample_data(output_path=None, num_customers=500):
    """Generate a realistic e-commerce transaction dataset."""
    if output_path is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        output_path = os.path.join(data_dir, "sample_customer_data.csv")
    random.seed(42)

    # Product catalog with realistic prices
    products = [
        ("Wireless Mouse", 29.99), ("Mechanical Keyboard", 89.99),
        ("USB-C Hub", 45.00), ("Monitor Stand", 34.99),
        ("Webcam HD", 59.99), ("Desk Lamp", 24.99),
        ("Notebook Set", 12.99), ("Pen Pack", 6.99),
        ("Headphones", 79.99), ("Phone Case", 15.99),
        ("Laptop Sleeve", 22.99), ("Mouse Pad XL", 19.99),
        ("Cable Organizer", 9.99), ("Screen Cleaner", 7.99),
        ("Desk Organizer", 27.99), ("Bluetooth Speaker", 49.99),
        ("Power Bank", 35.99), ("Ergonomic Wrist Rest", 18.99),
        ("USB Flash Drive 64GB", 11.99), ("HDMI Cable 2m", 13.99),
    ]

    # Date range: 12 months ending recently
    end_date = datetime.date(2025, 12, 31)
    start_date = datetime.date(2025, 1, 1)
    date_range_days = (end_date - start_date).days

    # Customer behavior profiles to create natural clusters
    profiles = [
        # (weight, avg_orders, order_spread, avg_qty, recency_bias)
        # VIP / Champions
        {"weight": 0.10, "orders": (15, 30), "qty": (2, 6), "recency": "recent", "cancel_rate": 0.02},
        # Loyal Customers
        {"weight": 0.15, "orders": (8, 15), "qty": (1, 4), "recency": "recent", "cancel_rate": 0.03},
        # Potential Loyalists
        {"weight": 0.15, "orders": (4, 8), "qty": (1, 3), "recency": "recent", "cancel_rate": 0.05},
        # At Risk
        {"weight": 0.20, "orders": (5, 12), "qty": (1, 3), "recency": "old", "cancel_rate": 0.08},
        # Bargain Hunters (low monetary)
        {"weight": 0.15, "orders": (3, 8), "qty": (1, 2), "recency": "mixed", "cancel_rate": 0.04},
        # Churned / Lost
        {"weight": 0.15, "orders": (1, 3), "qty": (1, 2), "recency": "very_old", "cancel_rate": 0.10},
        # New Customers
        {"weight": 0.10, "orders": (1, 3), "qty": (1, 3), "recency": "very_recent", "cancel_rate": 0.05},
    ]

    rows = []
    invoice_counter = 100000
    customer_id = 10000

    for profile in profiles:
        n_customers = int(num_customers * profile["weight"])
        for _ in range(n_customers):
            customer_id += 1
            cid = f"C{customer_id}"
            n_orders = random.randint(*profile["orders"])

            for _ in range(n_orders):
                invoice_counter += 1

                # Determine if this is a cancellation
                is_cancel = random.random() < profile["cancel_rate"]
                inv_no = f"{'C' if is_cancel else ''}{invoice_counter}"

                # Pick date based on recency bias
                if profile["recency"] == "very_recent":
                    day_offset = random.randint(0, 30)
                elif profile["recency"] == "recent":
                    day_offset = random.randint(0, int(date_range_days * 0.4))
                elif profile["recency"] == "mixed":
                    day_offset = random.randint(0, date_range_days)
                elif profile["recency"] == "old":
                    day_offset = random.randint(int(date_range_days * 0.5), date_range_days)
                else:  # very_old
                    day_offset = random.randint(int(date_range_days * 0.7), date_range_days)

                order_date = end_date - datetime.timedelta(days=day_offset)

                # Items in this order
                n_items = random.randint(1, 4)
                for _ in range(n_items):
                    product, base_price = random.choice(products)
                    qty = random.randint(*profile["qty"])
                    if is_cancel:
                        qty = -qty

                    # Bargain hunters get cheaper products
                    if profile == profiles[4]:
                        price = round(base_price * random.uniform(0.3, 0.7), 2)
                    else:
                        price = round(base_price * random.uniform(0.85, 1.15), 2)

                    rows.append({
                        "InvoiceNo": inv_no,
                        "StockCode": f"SKU{random.randint(1000, 9999)}",
                        "Description": product,
                        "Quantity": qty,
                        "InvoiceDate": order_date.strftime("%Y-%m-%d"),
                        "UnitPrice": price,
                        "CustomerID": cid,
                        "Country": random.choice([
                            "United Kingdom", "France", "Germany", "Spain",
                            "United States", "Australia", "Canada", "India"
                        ]),
                    })

    # Add some rows with missing CustomerID (to test cleaning)
    for _ in range(50):
        invoice_counter += 1
        product, base_price = random.choice(products)
        rows.append({
            "InvoiceNo": str(invoice_counter),
            "StockCode": f"SKU{random.randint(1000, 9999)}",
            "Description": product,
            "Quantity": random.randint(1, 3),
            "InvoiceDate": (end_date - datetime.timedelta(days=random.randint(0, date_range_days))).strftime("%Y-%m-%d"),
            "UnitPrice": round(base_price * random.uniform(0.85, 1.15), 2),
            "CustomerID": "",
            "Country": "Unknown",
        })

    random.shuffle(rows)

    # Write CSV
    fieldnames = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    filepath = os.path.abspath(output_path)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} transactions for {num_customers} customers -> {filepath}")


if __name__ == "__main__":
    generate_sample_data()
