import pandas as pd
import numpy as np

def safe_divide(numerator, denominator):
    """
    Safely divides two series, handling division by zero and NaNs.
    Args:
        numerator: Pandas Series or float
        denominator: Pandas Series or float
    Returns:
        Pandas Series or float with division result, infinity/NaN handled.
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        result = numerator / denominator
        # Replace inf with 0 or NaN depending on preference. 
        # For financial ratios, extreme values can be misleading. keeping Nan for now.
        result = result.replace([np.inf, -np.inf], np.nan)
    return result

def calculate_growth_metrics(df):
    """Calculates growth metrics like Revenue and Net Profit Growth."""
    try:
        if 'Revenue' in df.columns:
            df['Revenue Growth (%)'] = df['Revenue'].pct_change() * 100
        
        if 'Net Profit' in df.columns:
            df['Net Profit Growth (%)'] = df['Net Profit'].pct_change() * 100
            
        if 'EBITDA' in df.columns:
             df['EBITDA Growth (%)'] = df['EBITDA'].pct_change() * 100
             
    except Exception as e:
        print(f"Error calculating growth metrics: {e}")
    return df

def calculate_margins(df):
    """Calculates profitability margins."""
    try:
        if 'Revenue' in df.columns:
            rev = df['Revenue']
            # Avoid division by zero if revenue is 0
            rev_safe = rev.replace(0, np.nan) 
            
            if 'Gross Profit' in df.columns:
                df['Gross Margin (%)'] = (df['Gross Profit'] / rev_safe) * 100
            
            if 'EBITDA' in df.columns:
                df['EBITDA Margin (%)'] = (df['EBITDA'] / rev_safe) * 100
            
            if 'Net Profit' in df.columns:
                df['Net Margin (%)'] = (df['Net Profit'] / rev_safe) * 100
    except Exception as e:
        print(f"Error calculating margins: {e}")
    return df

def calculate_liquidity_ratios(df):
    """Calculates liquidity ratios like Current Ratio."""
    try:
        if 'Current Assets' in df.columns and 'Current Liabilities' in df.columns:
            df['Current Ratio'] = safe_divide(df['Current Assets'], df['Current Liabilities'])
            
        # Quick Ratio (assuming Inventory is not explicitly provided, but if we had it: (CA - Inventory) / CL)
        # For now, we only have the standard columns.
        
        # Cash Ratio could be calculated if we had 'Cash & Equivalents', but we only have 'Operating Cash Flow' which is different.
    except Exception as e:
        print(f"Error calculating liquidity ratios: {e}")
    return df

def calculate_leverage_ratios(df):
    """Calculates leverage ratios like Debt-to-Equity."""
    try:
        if 'Total Debt' in df.columns:
            if 'Equity' in df.columns:
                df['Debt-to-Equity'] = safe_divide(df['Total Debt'], df['Equity'])
            
            if 'Total Assets' in df.columns:
                df['Debt Ratio'] = safe_divide(df['Total Debt'], df['Total Assets'])
    except Exception as e:
        print(f"Error calculating leverage ratios: {e}")
    return df

def calculate_return_metrics(df):
    """Calculates return metrics like ROA and ROE."""
    try:
        if 'Net Profit' in df.columns:
            if 'Total Assets' in df.columns:
                # Using average assets is better, but ending assets is common for simple analysis
                df['ROA (%)'] = safe_divide(df['Net Profit'], df['Total Assets']) * 100
            
            if 'Equity' in df.columns:
                df['ROE (%)'] = safe_divide(df['Net Profit'], df['Equity']) * 100
    except Exception as e:
        print(f"Error calculating return metrics: {e}")
    return df

def calculate_indian_ratios(df):
    """Calculates specific Indian financial ratios."""
    try:
        # 1. Return on Net Worth (RONW) = PAT / Net Worth (Equity + Reserves)
        # Note: 'Equity' in our schema usually refers to Share Capital + Reserves (Total Equity).
        # If 'Equity' is Total Equity, then RONW = ROE.
        if 'Net Profit' in df.columns and 'Equity' in df.columns:
            df['RONW (%)'] = safe_divide(df['Net Profit'], df['Equity']) * 100

        # 2. Return on Capital Employed (ROCE) = EBIT / Capital Employed
        # Capital Employed = Total Assets - Current Liabilities (or Equity + Long Term Debt)
        if 'EBITDA' in df.columns and 'Depreciation & Amortisation' in df.columns:
            ebit = df['EBITDA'] - df['Depreciation & Amortisation']
            df['EBIT'] = ebit
        elif 'Net Profit' in df.columns and 'Tax Expense' in df.columns and 'Finance Costs' in df.columns:
             df['EBIT'] = df['Net Profit'] + df['Tax Expense'] + df['Finance Costs']
             
        if 'EBIT' in df.columns:
            if 'Total Assets' in df.columns and 'Current Liabilities' in df.columns:
                cap_employed = df['Total Assets'] - df['Current Liabilities']
                df['ROCE (%)'] = safe_divide(df['EBIT'], cap_employed) * 100
                
        # 3. Interest Coverage Ratio (ICR) = EBIT / Finance Costs
        if 'EBIT' in df.columns and 'Finance Costs' in df.columns:
            df['Interest Coverage Ratio'] = safe_divide(df['EBIT'], df['Finance Costs'])
            
        # 4. Inventory Turnover = Revenue / Average Inventory (using closing for simplicity if avg not avail)
        # Ratio says Revenue / Inventories. 
        if 'Revenue' in df.columns and 'Inventories' in df.columns:
             df['Inventory Turnover'] = safe_divide(df['Revenue'], df['Inventories'])
             
        # 5. Trade Receivables Days = (Trade Receivables / Revenue) * 365
        if 'Trade Receivables' in df.columns and 'Revenue' in df.columns:
            df['Debtor Days'] = safe_divide(df['Trade Receivables'], df['Revenue']) * 365
            
        # 6. Trade Payables Days = (Trade Payables / COGS) * 365
        # COGS proxy: Cost of Materials + Purchases + Changes in Inventory
        cogs = pd.Series(0, index=df.index)
        if 'Cost of Materials Consumed' in df.columns: cogs += df['Cost of Materials Consumed'].fillna(0)
        if 'Purchases of Stock-in-Trade' in df.columns: cogs += df['Purchases of Stock-in-Trade'].fillna(0)
        if 'Changes in Inventories' in df.columns: cogs += df['Changes in Inventories'].fillna(0) # Note: Change is (Op - Cl) or (Cl - Op)? Usually expensed.
        # If no detailed COGS components, maybe allow a 'COGS' column if fuzzy matched? 
        # For now, if cogs is 0, we can't calc.
        
        if 'Trade Payables' in df.columns:
            # Avoid div by zero
            cogs_cleaned = cogs.replace(0, np.nan)
            df['Creditor Days'] = safe_divide(df['Trade Payables'], cogs_cleaned) * 365

        # 7. Debt Service Coverage Ratio (DSCR) = (PAT + Dep + Interest) / (Interest + Principal Repayment)
        # We don't have Principal Repayment in std P&L. Assuming Interest only for denominator implies ICR.
        # If we take just (Net Income + Dep) / Total Debt? No, user said "Total Debt Service".
        # Proxy: (EBITDA - Tax) / (Interest + Current Maturity of LT Debt). We don't have Current Maturity.
        # User def: Net Income + Depreciation / Total Debt Service.
        # Without Principal Repayment data, we can't calculate exact DSCR.
        # We will calculate (Net Profit + Dep + Finance Costs) / Finance Costs as a proxy if Principal missing?
        # Or just skip if data missing. Let's use (Net Profit + Dep + Finance Costs) / Finance Costs as a "Cash Interest Coverage"
        if 'Net Profit' in df.columns and 'Depreciation & Amortisation' in df.columns and 'Finance Costs' in df.columns:
             numerator = df['Net Profit'] + df['Depreciation & Amortisation'] + df['Finance Costs']
             df['DSCR (Proxy)'] = safe_divide(numerator, df['Finance Costs'])

    except Exception as e:
        print(f"Error calculating Indian ratios: {e}")
    return df

def calculate_financial_ratios(df):
    """
    Master function to calculate all financial ratios.
    Args:
        df: DataFrame with standardized columns.
    Returns:
        df: DataFrame with all calculated ratios.
    """
    # Ensure dataframe is not empty
    if df.empty:
        return df
        
    df = calculate_growth_metrics(df)
    df = calculate_margins(df)
    df = calculate_liquidity_ratios(df)
    df = calculate_leverage_ratios(df)
    df = calculate_return_metrics(df)
    
    # Cash Flow specific
    if 'Operating Cash Flow' in df.columns and 'Net Profit' in df.columns:
         df['Cash Flow to Net Income'] = safe_divide(df['Operating Cash Flow'], df['Net Profit'])

    # Indian Specific Ratios
    df = calculate_indian_ratios(df)

    # Fill infinite values with NaN for safer display/plotting
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    return df
