# Business Research Engine

## Overview
The Business Research Engine is a Streamlit-based application designed to help users analyze financial statement data. It automates the calculation of key financial metrics, visualizes trends, and provides a risk assessment based on the provided data.

## Features
- **Data Upload**: Support for CSV and Excel files.
- **Automated Analysis**: Calculates growth, margins, liquidity, leverage, and return metrics.
- **Visualizations**: Interactive charts for revenue, profit, margins, and capital structure.
- **Risk Assessment**: automated red-flag detection and risk scoring.

## Prerequisites
- Python 3.8 or higher installed on your system.

## Installation & Setup

1.  **Clone or Download** the repository to your local machine.
2.  **Open a terminal** (Command Prompt or PowerShell) and navigate to the project folder.
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

### Method 1: One-Click Script (Windows)
Double-click the `run_app.bat` file in the project directory. This script will automatically install dependencies and launch the application.

### Method 2: Manual Start
Run the following command in your terminal:
```bash
streamlit run app.py
```

## Data Format
The application expects a CSV or Excel file with the following columns:
- Year
- Revenue
- Gross Profit
- EBITDA
- Net Profit
- Total Assets
- Total Debt
- Equity
- Current Assets
- Current Liabilities
- Operating Cash Flow
