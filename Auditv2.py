import streamlit as st
import pandas as pd
import re
import pdfplumber
from io import BytesIO

# --- Page Setup ---
st.set_page_config(page_title="PrintShop Analysis Pro", layout="wide")
st.title("🖨️ Printing Business: Financial & Product Report")

# --- Sidebar: Operational & Material Costs ---
st.sidebar.header("🏢 Fixed Costs")
monthly_rent = st.sidebar.number_input("Monthly Rent (PHP)", value=75000.0)
plate_rate = st.sidebar.number_input("Plate Multiplier", value=275.0)

st.sidebar.header("📦 Material & Unit Costs")
costs_map = {
    'Digital Print': st.sidebar.number_input("Digital Print (1-Side)", value=3.50),
    'Sticker': st.sidebar.number_input("Sticker (YB/BB)", value=3.25),
    'C2S 220': st.sidebar.number_input("C2S 220 / FC", value=2.87),
    'C2S 180': st.sidebar.number_input("C2S 180", value=2.57),
    'C2S 140': st.sidebar.number_input("C2S 140", value=1.60),
    'C2S 120': st.sidebar.number_input("C2S 120", value=1.59),
    'C2S 80': st.sidebar.number_input("C2S 80 / Book 80", value=1.04),
}

# --- Numeric Cleaning Function ---
def clean_num(x):
    if pd.isna(x) or x == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    s = re.sub(r'[^\d.]', '', str(x))
    try:
        return float(s)
    except:
        return 0.0

# --- File Loader ---
def load_and_clean(file):
    ext = file.name.split('.')[-1].lower()
    if ext == 'csv': df = pd.read_csv(file)
    elif ext == 'xlsx': df = pd.read_excel(file)
    elif ext == 'pdf':
        with pdfplumber.open(file) as pdf:
            rows = []
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    if not rows: rows.extend(table)
                    else: rows.extend(table[1:])
            df = pd.DataFrame(rows[1:], columns=rows[0]) if rows else None
    else: return None

    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Total', 'Discount', 'Sales Qty', 'Amount']:
        if col in df.columns:
            df[col] = df[col].apply(clean_num)
    
    df = df[df['Item Name'].notna() & df['Customer Name'].notna()].copy()
    
    if 'Sales Date' in df.columns:
        df['Sales Date'] = pd.to_datetime(df['Sales Date'], errors='coerce', dayfirst=True)
        df = df.dropna(subset=['Sales Date'])
        df['Month'] = df['Sales Date'].dt.to_period('M')
    return df

# --- Advanced Cost Logic ---
def run_math(df):
    dim_pattern = re.compile(r'(\d+)\s*[xX*]\s*(\d+)')
    def get_costs(row):
        item = str(row['Item Name']).upper()
        match = dim_pattern.search(item)
        if match and 'BANNER' not in item:
            w, h = int(match.group(1)), int(match.group(2))
            if w > 100: return (w/1000.0) * (h/1000.0) * plate_rate
        
        if 'DIGITAL' in item: return costs_map['Digital Print']
        if 'STICKER' in item: return costs_map['Sticker']
        if any(x in item for x in ['C2S 220', 'FC', 'FOLDCOTE']): return costs_map['C2S 220']
        if 'C2S 180' in item: return costs_map['C2S 180']
        if 'C2S 140' in item: return costs_map['C2S 140']
        if 'C2S 120' in item: return costs_map['C2S 120']
        if 'C2S 80' in item or 'BOOK 80' in item: return costs_map['C2S 80']
        return 0
        
    df['Unit Cost'] = df.apply(get_costs, axis=1)
    df['Prod Cost'] = df['Unit Cost'] * df['Sales Qty']
    return df

# --- App Logic ---
uploaded_file = st.file_uploader("Upload Report (CSV, XLSX, PDF)", type=["csv", "xlsx", "pdf"])

if uploaded_file:
    df = load_and_clean(uploaded_file)
    if df is not None:
        df = run_math(df)

        # Totals
        rev = df['Total'].sum()
        prod_cost = df['Prod Cost'].sum()
        rent_annual = 12 * monthly_rent
        net_profit = rev - prod_cost - rent_annual
        margin = (net_profit / rev * 100) if rev > 0 else 0

        # --- Financial Summary (Plain Text) ---
        st.header("📈 2025 Financial Summary")
        st.write(f"### **Gross Revenue:** PHP {rev:,.2f}")
        st.write(f"### **Net Profit (After Rent):** PHP {net_profit:,.2f}")
        st.write(f"### **Net Margin:** {margin:.1f}%")
        st.write(f"### **Annual Machine Rent:** PHP {rent_annual:,.2f}")
        
        st.divider()

        # --- Tabs ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Performance Charts", 
            "👥 Client Assessment", 
            "📦 Product & Services Assessment", 
            "🧠 Strategic Analysis"
        ])

        with tab1:
            st.subheader("Monthly Revenue vs Net Profit")
            monthly = df.groupby('Month').agg({'Total':'sum', 'Prod Cost':'sum'}).reset_index()
            monthly['Profit'] = monthly['Total'] - monthly['Prod Cost'] - monthly_rent
            monthly['Month_Label'] = monthly['Month'].astype(str)
            st.line_chart(monthly.set_index('Month_Label')[['Total', 'Profit']])

        with tab2:
            st.subheader("Top 10 Most Profitable Clients")
            client_data = df.groupby('Customer Name').agg({'Total':'sum', 'Prod Cost':'sum'})
            client_data['Profit'] = client_data['Total'] - client_data['Prod Cost']
            top_10_c = client_data.sort_values('Profit', ascending=False).head(10)
            st.table(top_10_c[['Total', 'Profit']].rename(columns={'Total':'Gross Sales', 'Profit':'Net Profit'}))
            st.bar_chart(top_10_c['Profit'])

        with tab3:
            st.subheader("Product & Services Deep-Dive")
            product_data = df.groupby('Item Name').agg({
                'Sales Qty': 'sum',
                'Total': 'sum',
                'Prod Cost': 'sum'
            })
            product_data['Net Profit'] = product_data['Total'] - product_data['Prod Cost']
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.write("**Highest Rated (By Sales Volume)**")
                top_qty = product_data.sort_values('Sales Qty', ascending=False).head(10)
                st.dataframe(top_qty[['Sales Qty', 'Net Profit']])
                st.write("*These products show your market popularity.*")
                
            with col_b:
                st.write("**Highest Profit Generators**")
                top_profit = product_data.sort_values('Net Profit', ascending=False).head(10)
                st.dataframe(top_profit[['Net Profit', 'Sales Qty']])
                st.write("*These products are the real 'money makers' for the business.*")

            st.divider()
            st.write("### Product Strategic Analysis")
            # Logic to find "High Volume but Low Profit" items
            product_data['Profit per Unit'] = product_data['Net Profit'] / product_data['Sales Qty']
            avg_profit_per_unit = product_data['Profit per Unit'].mean()
            leaks = product_data[(product_data['Profit per Unit'] < (avg_profit_per_unit * 0.5)) & (product_data['Sales Qty'] > 100)]
            
            if not leaks.empty:
                st.warning(f"Found {len(leaks)} high-volume products with very low margins. Consider adjusting prices for these items.")
                st.dataframe(leaks[['Sales Qty', 'Net Profit', 'Profit per Unit']])

        with tab4:
            st.subheader("Executive Strategy")
            st.write("**Key Problems:**")
            st.error(f"High Discounting: Total discounts given reach PHP {df['Discount'].sum():,.2f}.")
            st.warning(f"Rent Ratio: Rent consumes {(rent_annual/rev*100):.1f}% of gross income.")
            st.write("**Growth Potential:**")
            st.info(f"Shifting volume to your top 3 'Highest Profit Generator' products would scale the business without increasing rent costs.")

        # Export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Final Analysis CSV", csv, "Final_Analysis.csv", "text/csv")
else:
    st.info("Upload your report to generate the investor-ready dashboard.")
