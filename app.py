import streamlit as st
import pandas as pd
from src.data_processor import load_data, clean_data
from src.financial_analyzer import calculate_metrics, analyze_risk
from src.visualizer import plot_revenue_profit, plot_margins, plot_debt_equity, plot_cash_flow_vs_income

st.set_page_config(page_title="Business Research Engine", layout="wide")

st.title("Business Research Engine")
st.markdown("Upload financial data to generate insights, visualize trends, and assess risk.")

# Sidebar for File Upload & Configuration
st.sidebar.header("Configuration")
company_type = st.sidebar.selectbox("Company Classification (Schedule I)", 
                                    ["Private Limited", "Public Limited", "Listed Entity", "One Person Company"])

from src.pdf_extractor import PDFExtractor
from src.data_merger import merge_financial_data

st.sidebar.header("Upload Data")
uploaded_files = st.sidebar.file_uploader("Upload Annual Reports (One per Year)", 
                                          type=["csv", "xlsx", "xls", "pdf"], 
                                          accept_multiple_files=True)

# Session state to store processed separate DFs
if 'processed_files' not in st.session_state:
    st.session_state['processed_files'] = {} # Key: filename, Value: {'df': df, 'year': yr, 'method': m}

# Process newly uploaded files
if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state['processed_files']:
            # Process File
            df_temp = None
            method = "Unknown"
            year = None
            
            with st.spinner(f"Processing {file.name}..."):
                try:
                    if file.name.lower().endswith('.pdf'):
                        extractor = PDFExtractor()
                        file_bytes = file.getvalue()
                        df_temp, method = extractor.extract(file_bytes)
                        
                        # Try to detect year
                        # We need raw text again or PDFExtractor should return it/expose year
                        # For now, let's assume extract() sets internal state if we modified it?
                        # No, we just added a method. We need to call it.
                        # Extract text again lightly? No, let PDFExtractor return Year?
                        # Let's use the helper we just added on raw text. 
                        # This requires refactoring extract() to return metadata or text.
                        # For speed, let's re-extract text briefly or assume df has 'Year'.
                        
                        # If df has 'Year' and it's not "Current Year", use it.
                        if not df_temp.empty and 'Year' in df_temp.columns:
                            y_val = df_temp['Year'].iloc[0]
                            if isinstance(y_val, int): year = y_val
                        
                        # Fallback: Extract text for regex
                        if not year:
                            # Quick text extract for year detection
                            try:
                                from pdfminer.high_level import extract_text as p_extract
                                import io
                                raw_txt = p_extract(io.BytesIO(file_bytes), maxpages=5) # Check first 5 pages
                                detected_yr = extractor.extract_fiscal_year(raw_txt)
                                if detected_yr: year = detected_yr
                            except: pass

                    else:
                        # CSV/Excel
                        raw_df = load_data(file)
                        df_temp, _ = clean_data(raw_df)
                        method = "CSV/Excel"
                        if 'Year' in df_temp.columns and not df_temp.empty:
                            year = df_temp['Year'].iloc[0] # Assume one year per file
                
                except Exception as e:
                    st.sidebar.error(f"Error in {file.name}: {e}")
                    
                if df_temp is not None:
                     st.session_state['processed_files'][file.name] = {
                         'df': df_temp,
                         'year': year if year else "Unknown",
                         'method': method
                     }

# --- File Manager UI ---
if st.session_state['processed_files']:
    st.sidebar.subheader("File Manager")
    
    files_to_remove = []
    
    # Sort files by name or Year
    sorted_files = sorted(st.session_state['processed_files'].items(), 
                          key=lambda x: x[1]['year'] if isinstance(x[1]['year'], int) else 9999)

    for fname, data in sorted_files:
        with st.sidebar.expander(f"{fname} ({data['year']})"):
            st.write(f"Method: {data['method']}")
            
            # Manual Year Override
            new_year = st.number_input(f"Fiscal Year for {fname}", 
                                       min_value=1990, max_value=2030, 
                                       value=data['year'] if isinstance(data['year'], int) else 2024,
                                       key=f"year_{fname}")
            
            if new_year != data['year']:
                st.session_state['processed_files'][fname]['year'] = int(new_year)
                # Update DF year col
                if data['df'] is not None:
                    data['df']['Year'] = int(new_year)
                st.rerun()
                
            if st.button(f"Remove {fname}", key=f"del_{fname}"):
                files_to_remove.append(fname)
    
    # Apply removal
    if files_to_remove:
        for f in files_to_remove:
            del st.session_state['processed_files'][f]
        st.rerun()


# --- Main Logic on Merged Data ---
processed_data = st.session_state['processed_files']

if processed_data:
    # 1. Prepare List of DFs
    dfs_to_merge = [d['df'] for d in processed_data.values() if d['df'] is not None]
    
    # 2. Merge
    if dfs_to_merge:
        df, conflicts = merge_financial_data(dfs_to_merge)
        
        # 3. Validation
        if len(dfs_to_merge) < 3:
            st.warning(f"You have uploaded {len(dfs_to_merge)} years of data. We recommend at least 3 years for meaningful trend analysis.")
        
        # 4. Restatement Warnings
        if conflicts:
            st.error(f"⚠️ {len(conflicts)} data conflicts (possible restatements) detected!")
            with st.expander("View Conflict Details"):
                for c in conflicts:
                    st.write(f"**{c['Metric']} ({c['Year']})**: Found values {c['Values']}. Using {c['Values'][-1]}.")
        
        # 5. Application Flow (Using existing Tabs)
        # We need to map our logic to the existing tabs.
        
        # Clean & Metrics (already cleaned individually, but need metrics on merged)
        # Note: DFs were cleaned individually, but merging might produce partial rows.
        # We need to re-run calculate_metrics on the merged DF if metrics rely on X vs Y
        # (e.g. Growth relies on prev year row). 
        # Existing calculate_metrics expects one DF with all years. Perfect.
        
        df = calculate_metrics(df)
        risk_report = analyze_risk(df)
        
        # Add restatement flag to risk report if needed
        if conflicts:
            risk_report['red_flags'].append(f"Data Integrity detected {len(conflicts)} possible restatements/conflicts between uploaded files.")
            if risk_report['risk_level'] == "Low": risk_report['risk_level'] = "Moderate" # Bump risk
            
        # --- UI TABS ---
        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Financial Analysis", "Risk Report", "Indian FS Analysis"])

        with tab1:
            st.header("Financial Overview")
            st.badge(company_type)

            # --- Master CSV Download ---
            st.download_button("Download Merged Dataset (CSV)", 
                               df.to_csv(index=False).encode('utf-8'), 
                               "master_financials.csv", "text/csv")
            
            # Key Metrics (Most recent year)
            if not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else None
                
                col1, col2, col3, col4 = st.columns(4)
                
                col1.metric("Revenue", f"${latest['Revenue']:,.0f}" if 'Revenue' in latest else "N/A", 
                            f"{latest['Revenue Growth (%)']:.1f}%" if prev is not None and 'Revenue Growth (%)' in latest else None)
                col2.metric("Net Profit", f"${latest['Net Profit']:,.0f}" if 'Net Profit' in latest else "N/A", 
                            f"{latest['Net Profit Growth (%)']:.1f}%" if prev is not None and 'Net Profit Growth (%)' in latest else None)
                if 'Gross Margin (%)' in latest:
                    col3.metric("Gross Margin", f"{latest['Gross Margin (%)']:.1f}%")
                if 'Net Margin (%)' in latest:
                    col4.metric("Net Margin", f"{latest['Net Margin (%)']:.1f}%")

            st.subheader("Data Preview")
            st.dataframe(df.style.format(precision=2))

        with tab2:
            st.header("Deep Dive Analysis")
            if not df.empty:
                 # Display New Ratios 
                st.subheader("Key Ratios")
                latest = df.iloc[-1]
                
                c1, c2, c3, c4 = st.columns(4)
                if 'Current Ratio' in df.columns: c1.metric("Current Ratio", f"{latest['Current Ratio']:.2f}")
                if 'Debt-to-Equity' in df.columns: c2.metric("Debt-to-Equity", f"{latest['Debt-to-Equity']:.2f}")
                if 'ROA (%)' in df.columns: c3.metric("ROA", f"{latest['ROA (%)']:.1f}%")
                if 'ROE (%)' in df.columns: c4.metric("ROE", f"{latest['ROE (%)']:.1f}%")

                st.divider()

                col1, col2 = st.columns(2)
                
                with col1:
                    if 'Revenue' in df.columns: st.plotly_chart(plot_revenue_profit(df), use_container_width=True)
                    if 'Total Debt' in df.columns and 'Equity' in df.columns:
                        st.plotly_chart(plot_debt_equity(df), use_container_width=True)
                    
                with col2:
                    if 'Gross Margin (%)' in df.columns: st.plotly_chart(plot_margins(df), use_container_width=True)
                    if 'Operating Cash Flow' in df.columns:
                        st.plotly_chart(plot_cash_flow_vs_income(df), use_container_width=True)

        with tab3:
            st.header("Automated Risk Assessment")
            
            level = risk_report["risk_level"]
            color = "green" if level == "Low" else "orange" if level == "Moderate" else "red"
            
            st.markdown(f"### Overall Risk Level: :{color}[{level}]")
            
            if risk_report["red_flags"]:
                st.warning("Potential Red Flags Detected:")
                for flag in risk_report["red_flags"]:
                    st.markdown(f"- {flag}")
            else:
                st.success("No major red flags detected based on the analysis logic.")
                
        with tab4:
            st.header(f"Schedule III Analysis ({company_type})")
            
            if not df.empty:
                # Indian Ratios Display
                st.subheader("Indian Financial Ratios (ICAI/SEBI)")
                ratios_cols = ['RONW (%)', 'ROCE (%)', 'Interest Coverage Ratio', 'Inventory Turnover', 'Debtor Days', 'Creditor Days', 'DSCR (Proxy)']
                
                valid_ratios = [c for c in ratios_cols if c in df.columns]
                
                if valid_ratios:
                    latest = df.iloc[-1]
                    cols = st.columns(len(valid_ratios))
                    for i, r in enumerate(valid_ratios):
                        val = latest[r]
                        if pd.notna(val):
                            cols[i].metric(r, f"{val:.2f}")
                        else:
                            cols[i].metric(r, "N/A")
                
                st.divider()
                
                # Structured Schedule III Tables
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("Balance Sheet (Trend)")
                    bs_items = ["Share Capital", "Reserves & Surplus", "Long-Term Borrowings", "Deferred Tax Liabilities", "Short-Term Borrowings", "Trade Payables"]
                    bs_cols = ["Year"] + [c for c in bs_items if c in df.columns]
                    st.dataframe(df[bs_cols].set_index("Year").style.format(precision=0))

                with c2:
                    st.subheader("Profit & Loss (Trend)")
                    pl_items = ["Revenue from Operations", "Other Income", "Cost of Materials Consumed", "Employee Benefits Expense", "Finance Costs", "Depreciation & Amortisation", "Other Expenses", "Tax Expense", "Net Profit"]
                    pl_cols = ["Year"] + [c for c in pl_items if c in df.columns]
                    st.dataframe(df[pl_cols].set_index("Year").style.format(precision=0))
    


else:
    st.info("Awaiting file upload.")
    
    with st.expander("Or Enter Data Manually", expanded=True):
        st.write("### Manual Data Entry")
        
        # --- Configuration ---
        c1, c2, c3 = st.columns(3)
        with c1:
            num_years = st.select_slider("Number of Years", options=[3, 5, 7, 10], value=5)
        with c2:
            end_year = st.selectbox("Ending Fiscal Year", options=[2026, 2025, 2024, 2023, 2022], index=2)
        with c3:
            input_unit = st.radio("Input Unit", ["Rupees", "Lakhs", "Crores"], horizontal=True)
            
        # --- Feature Unlock System ---
        st.write("Analysis Capabilities Unlocked:")
        cols = st.columns(4)
        defaults = {"Basic Ratios": 3, "Red Flags": 3, "CAGR Analysis": 5, "Cycle Analysis": 10}
        for i, (feat, min_y) in enumerate(defaults.items()):
            if num_years >= min_y:
                cols[i].success(f"✅ {feat}")
            else:
                cols[i].caption(f"🔒 {feat} ({min_y}+ yrs)")
        
        # --- Dynamic Grid Generation ---
        years = [end_year - i for i in range(num_years)]
        years.sort(reverse=True) # Descending for columns? usually tables have ascending or descending. 
        # Financials usually Year 1, Year 2... let's keep ascending for DataFrame logical processing
        # But for entry, maybe Descending (Latest first) is more natural? 
        # Let's pivot: Columns = Years.
        years_sorted = sorted(years)
        
        # Defined Rows based on Schedule III (Subset for manual entry)
        manual_rows = [
            "Revenue from Operations", "Other Income", 
            "Cost of Materials Consumed", "Employee Benefits Expense", 
            "Finance Costs", "Depreciation & Amortisation", "Other Expenses", "Tax Expense",
            "Net Profit", 
            "Share Capital", "Reserves & Surplus", 
            "Long-Term Borrowings", "Short-Term Borrowings",
            "Trade Payables", "Fixed Assets", # Mapped to Tangible Assets
            "Trade Receivables", "Inventories", "Cash & Cash Equivalents",
            "Total Assets", "Current Liabilities"
        ]
        
        # Prepare Data
        # Check if we have extracted data to preload
        preload_data = {}
        if 'processed_files' in st.session_state and st.session_state['processed_files']:
            # Try to populate from uploaded files if user switches
            pass 
        
        # Create Template DF
        # Index = Metric, Columns = Years
        grid_df = pd.DataFrame(index=manual_rows, columns=years_sorted).fillna(0.0)
        
        st.write("Enter financials below:")
        edited_grid = st.data_editor(grid_df, use_container_width=True)
        
        if st.button("Run Analysis"):
            with st.spinner("Processing..."):
                # 1. Transpose to Wide Format (Index=Year, Cols=Metrics)
                # Current: Index=Metric, Cols=Year
                # Transpose -> Index=Year, Cols=Metric
                df_input = edited_grid.T
                
                # 2. Reset Index to make Year a column
                df_input.index.name = "Year"
                df_input = df_input.reset_index()
                
                # 3. Unit Conversion
                multiplier = 1
                if input_unit == "Lakhs": multiplier = 100_000
                if input_unit == "Crores": multiplier = 100_000_00
                
                # Apply multiplier to all except Year
                numeric_cols = df_input.columns.drop("Year")
                df_input[numeric_cols] = df_input[numeric_cols].astype(float) * multiplier
                
                # 4. Map columns to what app expects
                # App expects standard names from Data Processor/clean_data
                # We used standard names in rows, so we are mostly good.
                # However, calculate_metrics might rely on specific columns being present.
                # Let's ensure 'Revenue' is there (mapped from Revenue from Operations)
                # data_processor.clean_data does renaming. 
                # Let's manually apply key renames to be safe for ratios
                # 'Revenue from Operations' -> 'Revenue' (if needed, but clean_data keeps standard names)
                # existing app uses latest['Revenue']? 
                # Wait, standard name IS "Revenue from Operations". 
                # So if app uses ['Revenue'], it must be renaming it somewhere or using fuzzy match "Revenue" -> "Revenue from Operations"?
                # No, clean_data renames Mapped -> Standard. 
                # So the DF has "Revenue from Operations".
                # But the app lines 272 use `latest['Revenue']`. 
                # This implies 'Revenue' is in the DF. 
                # Let's check clean_data again or app.py. 
                # app.py line 272: col1.metric("Revenue", ... latest['Revenue'] ...)
                # If Standard Name is "Revenue from Operations", then 'Revenue' key must be missing?
                # Ah, fuzzy matcher might map "Revenue" to "Revenue from Operations".
                # But if the DF column IS "Revenue from Operations", then latest['Revenue'] would fail unless 'Revenue' exists.
                # Maybe I misread app.py or data_processor. 
                # Let's assume the App needs "Revenue". 
                # I'll create an alias column 'Revenue' = 'Revenue from Operations' just in case.
                
                if "Revenue from Operations" in df_input.columns:
                     df_input["Revenue"] = df_input["Revenue from Operations"]
                     
                # 'Total Debt' = Long + Short
                if "Long-Term Borrowings" in df_input.columns and "Short-Term Borrowings" in df_input.columns:
                    df_input["Total Debt"] = df_input["Long-Term Borrowings"] + df_input["Short-Term Borrowings"]
                
                # 'Equity' = Share Cap + Reserves
                if "Share Capital" in df_input.columns and "Reserves & Surplus" in df_input.columns:
                    df_input["Equity"] = df_input["Share Capital"] + df_input["Reserves & Surplus"]
                    
                # Store in session state
                st.session_state['manual_df'] = df_input
                st.rerun()

    # Check for manual data in session state
    if 'manual_df' in st.session_state and not uploaded_files:
        df = st.session_state['manual_df']
        
        # Download Button for Manual Data
        st.download_button("Download Manual Data (CSV)", 
                           df.to_csv(index=False).encode('utf-8'), 
                           "manual_financials.csv", "text/csv")
                           
        st.success("Manual Data Loaded. Processing...")
        
        try:
             # Calculate Metrics
            df = calculate_metrics(df)
            risk_report = analyze_risk(df)
            
            # --- DASHBOARD RENDER (Reduced for Manual) ---
            t1, t2, t3, t4 = st.tabs(["Overview", "Financial Analysis", "Risk Report", "Indian FS Analysis"])
            
            latest = df.iloc[-1]
            with t1:
                rev_val = latest.get('Revenue', latest.get('Revenue from Operations', 0))
                st.metric("Revenue", f"${rev_val:,.0f}")
                
                net_profit_val = latest.get('Net Profit', 0)
                st.metric("Net Profit", f"${net_profit_val:,.0f}")
                
                st.dataframe(df)
            
            with t3:
                level = risk_report["risk_level"]
                st.markdown(f"### Overall Risk Level: {level}")
                for flag in risk_report["red_flags"]:
                    st.markdown(f"- {flag}")
            
            with t4:
                # Show Indian Ratios if possible
                st.subheader("Indian Financial Ratios")
                ratios_cols = ['RONW (%)', 'ROCE (%)', 'Interest Coverage Ratio', 'DSCR (Proxy)']
                valid_ratios = [c for c in ratios_cols if c in df.columns]
                
                if valid_ratios:
                    cols = st.columns(len(valid_ratios))
                    for i, r in enumerate(valid_ratios):
                        cols[i].metric(r, f"{latest[r]:.2f}")
                else:
                    st.info("Insufficient data for Indian ratios.")

        except Exception as e:
            st.error(f"Error in manual analysis: {e}")

    st.write("Upload a CSV/Excel/PDF file with columns like 'Revenue', 'Net Profit', 'Total Debt', etc.")
