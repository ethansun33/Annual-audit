with tab2:
        if fuji_df is not None:
            st.header("POS vs Printer Audit")
            
            # 1. POS Data Preparation
            # Extract numbers from "Invoice No." (e.g., DR15322 -> 15322)
            pos_df['DR_Num'] = pos_df['Invoice No.'].astype(str).str.extract(r'(\d+)').astype(float)
            
            # 2. Fuji Data Preparation
            # Extract numbers from "Job Name" (e.g., "Job_DR_15322" -> 15322)
            fuji_df['DR_Num'] = fuji_df['Job Name'].astype(str).str.extract(r'(\d+)').astype(float)
            fuji_df['Printed Pages'] = pd.to_numeric(fuji_df['Printed Pages'], errors='coerce').fillna(0)
            
            # 3. Aggregation
            pos_grouped = pos_df.groupby('DR_Num')['Sales Qty'].sum().reset_index()
            fuji_grouped = fuji_df.groupby('DR_Num')['Printed Pages'].sum().reset_index()
            
            # 4. Merging
            comparison = pd.merge(pos_grouped, fuji_grouped, on='DR_Num', how='outer', indicator=True)
            
            # 5. Display Results
            mismatches = comparison[comparison['Sales Qty'] != comparison['Printed Pages']]
            
            st.write("### Comparison Table")
            st.dataframe(comparison, use_container_width=True)
            
            if not mismatches.empty:
                st.error(f"Found {len(mismatches)} quantity discrepancies!")
                st.dataframe(mismatches)
            else:
                st.success("All quantities match perfectly!")
        else:
            st.warning("⚠️ Please upload the Fuji Printer Log in the sidebar to run the Production Audit.")