# Customer Segmentation Tool

An AI-powered full-stack web application that automatically segments customers from transaction data using **RFM Analysis** (Recency, Frequency, Monetary) and **K-Means Clustering**.

## Features

- **Multi-Format Upload:** Supports `.csv`, `.xlsx`, `.xls`, and `.zip` archives.
- **Smart Data Cleaning:** Automatically handles missing data, cancelled orders, and invalid prices.
- **Dynamic Clustering:** Uses Scikit-Learn to apply K-Means clustering. Configurable number of clusters (K=2 to 8).
- **Auto-Labeling:** Automatically labels segments (e.g., Champions, Loyal Customers, At Risk) based on relative RFM rankings.
- **Visualizations:** 
  - 3D Interactive Scatter Plot of RFM scores (using Plotly).
  - 2D PCA Projection (using Chart.js).
  - Elbow Method Chart to help decide the optimal number of clusters.
- **Responsive UI:** Premium dark theme with glassmorphism effects, optimized for both desktop and mobile devices.
- **Export Capabilities:** Download your segmented customer list as a clean CSV.

## Architecture

- **Backend:** Python / Flask (`backend/app.py`)
- **Frontend:** HTML, CSS, JavaScript (`frontend/`)
- **Machine Learning:** scikit-learn, pandas, numpy

## Repository Structure & File Map

```text
Customer-Segmentation-Tool/
├── backend/
│   ├── app.py                  # Main Flask backend application and REST API endpoints
│   ├── rfm_analysis.py         # RFM calculation, scaling, K-Means clustering, and segment labeling logic
│   ├── generate_sample_data.py # Script to generate mock customer transaction records for testing
│   └── run_segmentation.py     # CLI script to run RFM analysis on a dataset directly from terminal
├── data/                       # Workspace directory for raw and processed datasets (ignored in git)
├── frontend/
│   ├── index.html              # Dashboard user interface (HTML structure)
│   ├── style.css               # Custom styling with premium dark-mode glassmorphism
│   └── app.js                  # JavaScript logic for upload handling, API requests, and Plotly/Chart.js rendering
├── .gitignore                  # Git configurations to ignore pycache, venv, and large data files
└── README.md                   # Project documentation
```

## How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shalusaju88/Customer-Segmentation-Tool.git
   cd Customer-Segmentation-Tool
   ```

2. **Install Python dependencies:**
   Ensure you have Python installed, then install the required packages:
   ```bash
   pip install flask flask-cors pandas numpy scikit-learn openpyxl
   ```

3. **Start the Backend Server:**
   Run the Flask API server from the root of the project:
   ```bash
   python backend/app.py
   ```

4. **Access the Application:**
   Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Note on GitHub Pages

Because this application relies on a Python (Flask) backend to process data and run machine learning models, **it cannot be fully hosted on GitHub Pages** (which only supports static HTML/CSS/JS). To deploy this app live, you will need to host the backend on a service like Render, Heroku, or PythonAnywhere, and point the frontend to that new API URL.
