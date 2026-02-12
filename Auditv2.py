import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt

# --- Page Configuration ---
st.set_page_config(page_title="Printing Business Dashboard", layout="wide")
st.title("🖨️ Printing Business Financial Analyzer")
st.markdown("Upload your Annual Report to see real-time profit analysis and growth forecasts.")

# --- Sidebar: Interactive Parameters ---
st.sidebar.header("Operational Cost Settings")
plate_rate = st.sidebar.number_input("Plate Rate (Multiplier)", value=275)
monthly_rent = st.sidebar.number_input("Monthly Machine Rent (PHP)", value=75000)
print_cost_1s = st.sidebar.number_input("Digital Print Cost (1 Side)", value=3.50)

st.sidebar.subheader("Paper & Material Costs")
costs_map = {
    'YB/BB Sticker': st.sidebar.number_input("Sticker Price", value=3.25),
    'C2S 220 / FC': st.sidebar.number_input("C2S 220 / FC Price", value=2.87),
    'C2S 180': st.sidebar.number_input("C2S 180 Price", value=2.57),
    'C2S 140': st.sidebar.number_input("C2S 140 Price", value=1.60),
    'C2S 120': st.sidebar.number_input("C2S 120 Price", value=1.59),
    'C2S 80 / Book 80': st.sidebar.number_input("C2S 80 / Book 80 Price", value=1.04),
}

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload Annual Report (CSV)", type="csv")

if uploaded_file:
    # 1. Load Data
    df = pd.read_csv(uploaded_file)
    
    # 2. Data Cleaning
    for col in ['Amount', 'Total', 'Discount']:
        df[col] = pd.to_numeric(df[col].astype(str).replace('[\$,]', '', regex=True), errors='coerce').fillna(0)
    
    # Remove summary/empty rows
    df = df[df['Item Name'].notna() & df['Customer Name'].notna()].copy()
    df['Sales Date'] = pd.to_datetime(df['Sales Date'], dayfirst=True)
    df['Month'] = df['Sales Date'].dt.to_period('M')

    # 3. Cost Calculation Logic
    dim_pattern = re.compile(r'(\d+)\s*[xX*]\s*(\d+)')
    
    def calculate_costs(row):
        item = str(row['Item Name']).upper()
        # Plate Cost
        match = dim_pattern.search(item)
        if match and 'BANNER' not in item:
            w, h = int(match.group(1)), int(match.group(2))
            if w > 100 and h > 100:
                return (w/1000.0) * (h/1000.0) * plate_rate
        
        # Mapping Costs
        if 'DIGITAL PRINT 1 SIDE' in item: return print_cost_1s
        if 'STICKER' in item: return costs_map['YB/BB Sticker']
        if 'C2S 220' in item or 'FC' in item or 'FOLDCOTE' in item: return costs_map['C2S 220 / FC']
        if 'C2S 180' in item: return costs_map['C2S 180']
        if 'C2S 140' in item: return costs_map['C2S 140']
        if 'C2S 120' in item: return costs_map['C2S 120']
        if 'C2S 80' in item or 'BOOK 80' in item: return costs_map['C2S 80 / Book 80']
        return 0

    df['Unit Cost'] = df.apply(calculate_costs, axis=1)
    df['Total Production Cost'] = df['Unit Cost'] * df['Sales Qty']

    # 4. KPI Calculations
    total_rev = df['Total'].sum()
    total_prod_cost = df['Total Production Cost'].sum()
    total_rent = 12 * monthly_rent
    operating_profit = total_rev - total_prod_cost - total_rent
    margin = (operating_profit / total_rev) * 100 if total_rev > 0 else 0

    # Display Metrics
    st.subheader("High-Level Performance")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"P{total_rev:,.2f}")
    m2.metric("Total Prod. Cost", f"P{total_prod_cost:,.2f}")
    m3.metric("Operating Profit", f"P{operating_profit:,.2f}")
    m4.metric("Operating Margin", f"{margin:.2f}%")

    # 5. Visualizations
    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Monthly Revenue vs Profit")
        monthly_data = df.groupby('Month').agg({'Total': 'sum', 'Total Production Cost': 'sum'})
        monthly_data['Op_Profit'] = monthly_data['Total'] - monthly_data['Total Production Cost'] - monthly_rent
        st.line_chart(monthly_data[['Total', 'Op_Profit']])

    with col_right:
        st.subheader("Top 10 Profitable Clients")
        client_profit = df.groupby('Customer Name').agg({'Total': 'sum', 'Total Production Cost': 'sum'})
        client_profit['Profit'] = client_profit['Total'] - client_profit['Total Production Cost']
        st.bar_chart(client_profit['Profit'].sort_values(ascending=False).head(10))

    # 6. Simulation Section
    st.divider()
    st.subheader("💡 Investor 'What-If' Simulator")
    st.write("What happens if we reduce the average discount given to customers?")
    current_discount = df['Discount'].sum()
    reduction_pct = st.slider("Reduction in Discounting (%)", 0, 100, 10)
    potential_savings = current_discount * (reduction_pct / 100)
    
    st.info(f"By reducing discounts by {reduction_pct}%, you would save **P{potential_savings:,.2f}** in annual profit.")

else:
    st.info("Please upload your Annual Report CSV file in the sidebar to begin.")
