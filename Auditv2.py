import streamlit as st
import pandas as pd
import re
import io

# --- 1. GLOBAL INITIALIZATION ---
# These MUST be at the top level and outside any functions/ifs
pos_df = None
fuji_df = None

st.set_page_config(page_title="Print Suite v7", layout="wide")
st.title("📠 Print Suite: Audit & Financial Analytics")

# --- 2. SIDEBAR UPLOADS ---
st.sidebar.header("📂 Data Upload Center")

pos_file = st.sidebar.file_uploader("1. Sales Data (POS Report)", type=["csv", "xlsx"])
fuji_file = st.sidebar.file_uploader("2. Production Data (Fuji Log)", type=["csv", "xlsx"])

# --- 3. DATA PROCESSING ---
if pos_file is not None:
    try:
        if pos_file.name.endswith('.csv'):
            pos_df = pd.read_csv(pos_file)
        else:
            pos_df = pd.read_excel(pos_file)
        
        # Financial Data Cleaning
        if 'Total' in pos_df.columns:
            pos_df['Total'] = pd.to_numeric(pos_df['Total'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        if 'Sales Date' in pos_df.columns:
            pos_df['Sales Date'] = pd.to_datetime(pos_df['Sales Date'], dayfirst=True, errors='coerce')
    except Exception as e:
        st.error(f"Error loading POS file: {e}")

if fuji_file is not None:
    try:
        if fuji_file.name.endswith('.csv'):
            fuji_df = pd.read_csv(fuji_file)
        else:
            fuji_df = pd.read_excel(fuji_file)
    except Exception as e:
        st.error(f"Error loading Fuji file: {e}")

# --- 4. UI LOGIC ---
# This block only runs if pos_df was successfully created above
if pos_df is not None:
    tab1, tab2 = st.tabs(["📊 Financial Report", "🔍 Production Audit"])

    with tab1:
        st.header("Financial Performance")
        total_rev = pos_df['Total'].sum() if 'Total' in pos_df.columns else 0
        st.metric("Total Sales Revenue", f"${total_rev:,.2f}")
        
        if 'Sales Date' in pos_df.columns and not pos_df['Sales Date'].isnull().all():
            timeline = pos_df.groupby(pos_df['Sales Date'].dt.to_period('M'))['Total'].sum().reset_index()
            timeline['Sales Date'] = timeline['Sales Date'].astype(str)
            st.line_chart(timeline.set_index('Sales Date'))

    with tab2:
        if fuji_df is not None:
            # Audit Logic
            pos_audit = pos_df.copy()
            pos_audit['DR_Num'] = pos_audit['Invoice No.'].astype(str).str.extract(r'(\d+)').astype(float)
            
            # 2-Sided Calculation
            def calc_expected(row):
                qty = pd.to_numeric(str(row.get('Sales Qty', 0)).replace(',', ''), errors='coerce') or 0
                item = str(row.get('Item Name', '')).upper()
                return qty * 2 if '2 SIDES' in item else qty

            pos_audit['Expected_Pages'] = pos_audit.apply(calc_expected, axis=1)
            pos_grouped = pos_audit.groupby('DR_Num').agg({
                'Invoice No.': 'first',
                'Customer Name': 'first',
                'Expected_Pages': 'sum'
            }).reset_index()

            # Fuji Logic
            fuji_audit = fuji_df.copy()
            fuji_audit['DR_Num'] = fuji_audit['Job Name'].astype(str).str.extract(r'(\d+)').astype(float)
            fuji_audit['Printed Pages'] = pd.to_numeric(fuji_audit['Printed Pages'], errors='coerce').fillna(0)

            # Split Anonymous
            anon_df = fuji_audit[fuji_audit['DR_Num'].isna()].copy()
            fuji_grouped = fuji_audit[fuji_audit['DR_Num'].notna()].groupby('DR_Num')['Printed Pages'].sum().reset_index()

            # Merge
            comparison = pd.merge(pos_grouped, fuji_grouped, on='DR_Num', how='outer')
            comparison['Printed Pages'] = comparison['Printed Pages'].fillna(0)
            comparison['Diff'] = comparison['Printed Pages'] - comparison['Expected_Pages'].fillna(0)
            
            mismatches = comparison[comparison['Diff'] != 0].copy()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Billed Jobs", len(pos_grouped))
            c2.metric("Discrepancies", len(mismatches))
            c3.metric("Anonymous Jobs", len(anon_df))

            st.subheader("⚠️ Discrepancy List")
            st.dataframe(mismatches[['Invoice No.', 'Customer Name', 'Expected_Pages', 'Printed Pages', 'Diff']], use_container_width=True)

            # Export
            if not mismatches.empty:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    mismatches.to_excel(writer, index=False, sheet_name='Discrepancies')
                    anon_df.to_excel(writer, index=False, sheet_name='Anonymous')
                
                st.download_button("📥 Download Audit Report", output.getvalue(), "audit_report.xlsx")
        else:
            st.warning("Please upload the **Fuji Printer Log** to enable the Audit tab.")
else:
    st.info("👋 Welcome! Please upload your **POS Sales Data** in the sidebar to begin.")
