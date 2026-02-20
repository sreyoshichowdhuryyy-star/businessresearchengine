import pandas as pd
import numpy as np

def merge_financial_data(dfs):
    """
    Merges a list of single-year DataFrames into a unified multi-year DataFrame.
    Args:
        dfs: List of DataFrames, each containing 'Year' column and metrics.
    Returns:
        merged_df: Unified DataFrame with Years as rows (sorted).
        conflicts: List of dictionaries describing any data conflicts found.
    """
    if not dfs:
        return pd.DataFrame(), []

    # 1. Standardize and Concat
    # We want a long-format DF first: [Year, Metric, Value]
    # But our input DFs are wide: [Year, Rev, PAT...]
    
    combined = pd.concat(dfs, ignore_index=True)
    
    # 2. Check for Conflicts (Same Year, Multiple entries)
    # Group by Year and Metric is tricky in wide format.
    # Let's melt to long format for easier processing
    # ID vars = Year. All others are Value vars.
    long_df = combined.melt(id_vars=['Year'], var_name='Metric', value_name='Value')
    
    # Drop NaNs (metrics not present in a file)
    long_df = long_df.dropna(subset=['Value'])
    
    # Group by Year + Metric
    img_groups = long_df.groupby(['Year', 'Metric'])
    
    conflicts = []
    cleaned_rows = []
    
    for (year, metric), group in img_groups:
        values = group['Value'].tolist()
        
        # If multiple values for same Year/Metric
        if len(values) > 1:
            # Check if they are effectively the same (allow small diff for rounding)
            # We use a 2% threshold as requested
            v_min = min(values)
            v_max = max(values)
            
            # Avoid div by zero
            if v_min == 0:
                is_conflict = (v_max - v_min) > 0.01 # Abs diff if 0
            else:
                diff_pct = (v_max - v_min) / abs(v_min)
                is_conflict = diff_pct > 0.02
                
            if is_conflict:
                conflicts.append({
                    "Year": year,
                    "Metric": metric,
                    "Values": values,
                    "Message": f"Restatement or mismatch detected for {metric} in {year}: {values}"
                })
                # For now, take the LAST value (assuming latest report is most accurate/restated)
                final_val = values[-1] 
            else:
                # No significant conflict, average or take one
                final_val = values[-1] 
        else:
            final_val = values[0]
            
        cleaned_rows.append({"Year": year, "Metric": metric, "Value": final_val})
        
    # 3. Pivot back to Wide Format
    clean_long_df = pd.DataFrame(cleaned_rows)
    if clean_long_df.empty:
        return pd.DataFrame(), []
        
    merged_df = clean_long_df.pivot(index='Year', columns='Metric', values='Value').reset_index()
    
    # Sort by Year
    merged_df = merged_df.sort_values('Year').reset_index(drop=True)
    
    return merged_df, conflicts
