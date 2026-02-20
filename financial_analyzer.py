import pandas as pd
import numpy as np
from src.ratio_calculator import calculate_financial_ratios

def calculate_metrics(df):
    """
    Wrapper to use the robust ratio calculator.
    """
    return calculate_financial_ratios(df)

def analyze_risk(df):
    """
    Identifies red flags and assigns a risk score.
    Args:
        df: DataFrame with calculated metrics
    Returns:
        risk_report: Dictionary containing red flags, explanation, and score
    """
    red_flags = []
    
    # Check 1: Revenue Growing but OCF Declining (Last 2 periods if available)
    if len(df) >= 2:
        rev_growth = df['Revenue'].iloc[-1] > df['Revenue'].iloc[-2]
        ocf_decline = df['Operating Cash Flow'].iloc[-1] < df['Operating Cash Flow'].iloc[-2]
        if rev_growth and ocf_decline:
            red_flags.append("Revenue is growing, but Operating Cash Flow is declining. This may indicate poor earnings quality or aggressive revenue recognition.")

    # Check 2: Debt Growing Faster than Revenue (CAGR or simple growth if short period)
    if len(df) >= 2:
        debt_growth = (df['Total Debt'].iloc[-1] - df['Total Debt'].iloc[-2]) / df['Total Debt'].iloc[-2]
        rev_growth_rate = (df['Revenue'].iloc[-1] - df['Revenue'].iloc[-2]) / df['Revenue'].iloc[-2]
        
        if debt_growth > rev_growth_rate and debt_growth > 0:
            red_flags.append("Total Debt is growing faster than Revenue. This raises concerns about the sustainability of leverage.")

    # Check 3: Declining Margins (Last 3 years if available)
    if len(df) >= 3:
        margin_trend = df['Net Margin (%)'].iloc[-3:]
        if (margin_trend.iloc[1] < margin_trend.iloc[0]) and (margin_trend.iloc[2] < margin_trend.iloc[1]):
            red_flags.append("Net Profit Margin has declined for 3 consecutive years, suggesting deteriorating profitability or rising costs.")
    elif len(df) == 2:
         if df['Net Margin (%)'].iloc[-1] < df['Net Margin (%)'].iloc[-2]:
              # Not a strong red flag for just 1 year drop, maybe a warning or skip
              pass

    # Check 4: High Debt-to-Equity
    if df['Debt-to-Equity'].iloc[-1] > 2.0: # Threshold can be adjustable
        red_flags.append(f"Debt-to-Equity ratio is high ({df['Debt-to-Equity'].iloc[-1]:.2f}), indicating high leverage.")

    # --- Schedule III / Indian Specific Red Flags ---
    latest = df.iloc[-1]
    
    # 1. Receivable Days > 90
    if 'Debtor Days' in df.columns and latest['Debtor Days'] > 90:
        red_flags.append(f"Trade Receivables Days is high ({latest['Debtor Days']:.0f} days), indicating working capital stress.")
        
    # 2. Interest Coverage Ratio < 1.5
    if 'Interest Coverage Ratio' in df.columns and latest['Interest Coverage Ratio'] < 1.5:
        red_flags.append(f"Interest Coverage Ratio is low ({latest['Interest Coverage Ratio']:.2f}), indicating debt serviceability risk.")
        
    # 3. Negative Reserves & Surplus
    if 'Reserves & Surplus' in df.columns and latest['Reserves & Surplus'] < 0:
        red_flags.append("Reserves & Surplus is negative, indicating accumulated losses.")
        
    # 4. Short-Term Borrowings grow faster than Current Assets
    if 'Short-Term Borrowings' in df.columns and 'Current Assets' in df.columns and len(df) >= 2:
        stb_growth = (df['Short-Term Borrowings'].iloc[-1] - df['Short-Term Borrowings'].iloc[-2]) / df['Short-Term Borrowings'].iloc[-2]
        ca_growth = (df['Current Assets'].iloc[-1] - df['Current Assets'].iloc[-2]) / df['Current Assets'].iloc[-2]
        
        if stb_growth > ca_growth and stb_growth > 0:
             red_flags.append("Short-Term Borrowings dependancy is growing faster than Current Assets, allowing potential liquidity mismatch.")

    # 5. Finance Costs > 8% of Revenue
    if 'Finance Costs' in df.columns and 'Revenue' in df.columns and latest['Revenue'] > 0:
        fc_pct = (latest['Finance Costs'] / latest['Revenue']) * 100
        if fc_pct > 8:
            red_flags.append(f"Finance Costs are {fc_pct:.1f}% of Revenue (High), suggesting the company is over-leveraged.")

    # Risk Score Calculation
    score_val = len(red_flags)
    if score_val == 0:
        risk_level = "Low"
    elif score_val <= 2:
        risk_level = "Moderate"
    else:
        risk_level = "High"

    return {
        "risk_level": risk_level,
        "score": score_val,
        "red_flags": red_flags
    }
