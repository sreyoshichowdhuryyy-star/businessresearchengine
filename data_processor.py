import pandas as pd
import io
from thefuzz import process, fuzz

# Schedule III Schema: Standard Names -> Common Aliases
SCHEDULE_III_SCHEMA = {
    # Equity & Liabilities
    "Share Capital": ["Share Capital", "Equity Share Capital", "Preference Share Capital"],
    "Reserves & Surplus": ["Reserves & Surplus", "Other Equity", "Retained Earnings", "Gen Reserve", "Securities Premium"],
    "Long-Term Borrowings": ["Long-Term Borrowings", "Non-Current Borrowings", "Long Term Debt", "Term Loans"],
    "Deferred Tax Liabilities": ["Deferred Tax Liabilities", "DTL", "Deferred Tax Liability (Net)"],
    "Other Long-Term Liabilities": ["Other Long-Term Liabilities", "Other Non-Current Liabilities"],
    "Long-Term Provisions": ["Long-Term Provisions", "Non-Current Provisions"],
    "Short-Term Borrowings": ["Short-Term Borrowings", "Current Borrowings", "Short Term Debt", "Working Capital Loans", "CC/OD"],
    "Trade Payables": ["Trade Payables", "Sundry Creditors", "Creditors", "Accounts Payable"],
    "Other Current Liabilities": ["Other Current Liabilities", "Other Financial Liabilities (Current)"],
    "Short-Term Provisions": ["Short-Term Provisions", "Current Provisions", "Prov for Tax"],
    
    # Assets
    "Tangible Assets": ["Tangible Assets", "Property Plant & Equipment", "PPE", "Fixed Assets"],
    "Intangible Assets": ["Intangible Assets", "Goodwill", "Software", "Patents"],
    "Capital Work-in-Progress": ["Capital Work-in-Progress", "CWIP"],
    "Non-Current Investments": ["Non-Current Investments", "Long Term Investments"],
    "Long-Term Loans & Advances": ["Long-Term Loans & Advances", "Non-Current Loans"],
    "Other Non-Current Assets": ["Other Non-Current Assets", "Other Non Current Assets"],
    "Inventories": ["Inventories", "Stock", "Stock-in-Trade"],
    "Trade Receivables": ["Trade Receivables", "Sundry Debtors", "Debtors", "Accounts Receivable"],
    "Cash & Cash Equivalents": ["Cash & Cash Equivalents", "Cash and Bank Balances", "Cash"],
    "Short-Term Loans & Advances": ["Short-Term Loans & Advances", "Current Loans"],
    "Other Current Assets": ["Other Current Assets"],
    
    # Profit & Loss
    "Revenue from Operations": ["Revenue from Operations", "Revenue", "Sales", "Turnover", "Gross Sales", "Net Sales"],
    "Other Income": ["Other Income", "Non-Operating Income", "Interest Income"],
    "Cost of Materials Consumed": ["Cost of Materials Consumed", "Raw Material Consumed"],
    "Purchases of Stock-in-Trade": ["Purchases of Stock-in-Trade", "Purchases"],
    "Changes in Inventories": ["Changes in Inventories", "Change in Stock", "(Increase)/Decrease in Stock"],
    "Employee Benefits Expense": ["Employee Benefits Expense", "Staff Cost", "Salaries and Wages", "Manpower Cost"],
    "Finance Costs": ["Finance Costs", "Interest Expense", "Interest", "Finance Charges"],
    "Depreciation & Amortisation": ["Depreciation & Amortisation", "Depreciation", "Amortisation", "D&A"],
    "Other Expenses": ["Other Expenses", "Admin Expenses", "Selling Expenses", "Operating Expenses"],
    "Exceptional Items": ["Exceptional Items", "Exceptionals"],
    "Tax Expense": ["Tax Expense", "Current Tax", "Deferred Tax", "Total Tax", "Income Tax"],
    "Net Profit": ["Net Profit", "Profit After Tax", "PAT", "Net Income", "Profit for the Period"]
}

def load_data(file):
    """
    Loads data from a CSV or Excel file.
    Args:
        file: Uploaded file object (Streamlit UploadedFile)
    Returns:
        pd.DataFrame: Loaded data
    """
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    elif file.name.endswith('.xlsx') or file.name.endswith('.xls'):
        return pd.read_excel(file)
    else:
        raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")

def smart_column_mapping(df_columns):
    """
    Uses fuzzy matching to map input columns to Schedule III standard names.
    Args:
        df_columns: List of column names from the uploaded file.
    Returns:
        mapping: Dictionary {Standard Name: Mapped Column (or None)}
        mapping_details: Dictionary {Standard Name: {'mapped_val': ..., 'confidence': ..., 'method': ...}}
    """
    mapping = {}
    mapping_details = {}
    
    # Create a reverse map for fast exact lookup of common aliases
    alias_map = {}
    for std, aliases in SCHEDULE_III_SCHEMA.items():
        for alias in aliases:
            alias_map[alias.lower()] = std
            
    # Normalize input columns
    lower_cols = {col.lower(): col for col in df_columns}
    
    for std_name, aliases in SCHEDULE_III_SCHEMA.items():
        best_match = None
        best_score = 0
        match_method = "None"
        
        # 1. Exact Match on Standard Name
        if std_name.lower() in lower_cols:
            best_match = lower_cols[std_name.lower()]
            best_score = 100
            match_method = "Exact (Standard)"
            
        # 2. Exact Match on Aliases
        if not best_match:
            for alias in aliases:
                if alias.lower() in lower_cols:
                    best_match = lower_cols[alias.lower()]
                    best_score = 100
                    match_method = "Exact (Alias)"
                    break
        
        # 3. Fuzzy Match
        if not best_match:
            # We compare against all aliases + standard name
            candidates = aliases + [std_name]
            
            # Find the best match among all input columns for ANY of the candidates
            # extraction returns (best_candidate, score)
            # But we need to match input columns against our specific target list.
            
            # Strategy: For this standard field, find the best fuzzy match from input columns
            # We matched standard vs input.
            
            # Get best match from input columns for the standard name itself
            extract_std = process.extractOne(std_name, df_columns, scorer=fuzz.token_sort_ratio)
            
            current_best_col = extract_std[0]
            current_best_score = extract_std[1]
            
            # Check aliases too
            for alias in aliases:
                extract_alias = process.extractOne(alias, df_columns, scorer=fuzz.token_sort_ratio)
                if extract_alias[1] > current_best_score:
                    current_best_score = extract_alias[1]
                    current_best_col = extract_alias[0]
            
            # Threshold for accepting a fuzzy match
            if current_best_score >= 80:
                best_match = current_best_col
                best_score = current_best_score
                match_method = "Fuzzy"
        
        mapping[std_name] = best_match
        mapping_details[std_name] = {
            "mapped_col": best_match,
            "confidence": best_score,
            "method": match_method
        }
        
    return mapping, mapping_details

def clean_data(df):
    """
    Standardizes column names and ensures required columns exist using Smart Mapping.
    Args:
        df: Raw DataFrame
    Returns:
        pd.DataFrame: DataFrame with Standardized columns where found
        dict: The mapping details for review
    """
    
    # 1. Identify 'Year' column specifically first (essential)
    year_col = None
    for col in df.columns:
        if "year" in str(col).lower() or "period" in str(col).lower():
            year_col = col
            break
            
    # 2. Run Smart Mapping
    mapping, mapping_details = smart_column_mapping(df.columns)
    
    # 3. Rename columns based on mapping
    rename_dict = {}
    if year_col:
        rename_dict[year_col] = "Year"
        
    for std, mapped in mapping.items():
        if mapped:
            rename_dict[mapped] = std
            
    # We do NOT drop columns, we just rename the identified ones.
    # This allows users to keep other data if they want.
    df_clean = df.rename(columns=rename_dict)
    
    # 4. Sort by Year if present
    if 'Year' in df_clean.columns:
        try:
            df_clean = df_clean.sort_values('Year').reset_index(drop=True)
        except:
            pass # Keep original order if sorting fails
            
    return df_clean, mapping_details
