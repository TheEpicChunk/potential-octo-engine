import streamlit as st
import pandas as pd
import json
import os
import uuid

# Configuration for page layout
st.set_page_config(page_title="Pokémon Card Tracker", layout="wide")

DATA_FILE = "pokemon_tracker_data.json"

# --- DATA MANAGEMENT ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"paid_so_far": 0.0, "lots": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "app_data" not in st.session_state:
    st.session_state.app_data = load_data()

# --- SIDEBAR & GLOBAL METRICS ---
st.sidebar.title("📈 Pokémon Portfolio")

def update_paid():
    st.session_state.app_data["paid_so_far"] = st.session_state.paid_input
    save_data(st.session_state.app_data)

st.sidebar.number_input(
    "Total Paid So Far (\$)", 
    min_value=0.0, 
    value=float(st.session_state.app_data.get("paid_so_far", 0.0)),
    key="paid_input",
    on_change=update_paid
)

total_market = 0.0
total_selling = 0.0

# Calculate totals across all lots (Lot-level + Individual cards)
for lot_id, lot_data in st.session_state.app_data["lots"].items():
    # Add bulk lot pricing
    total_market += lot_data.get("lot_market_price", 0.0)
    total_selling += lot_data.get("lot_selling_price", 0.0)
    
    # Add individual card pricing
    for card in lot_data.get("cards", []):
        total_market += card.get("Market Price") or 0.0
        total_selling += card.get("Current Price") or 0.0

st.sidebar.divider()
st.sidebar.metric("Total Market Value", f"\${total_market:.2f}")
st.sidebar.metric("Total Selling Value", f"\${total_selling:.2f}")

paid_so_far = st.session_state.app_data.get("paid_so_far", 0.0)
potential_earnings = total_selling - paid_so_far

st.sidebar.metric("Potential Profit / Earnings", f"\${potential_earnings:.2f}")

if total_selling > 0:
    break_even = (paid_so_far / total_selling) * 100
    st.sidebar.metric(
        "Break-Even %", 
        f"{break_even:.1f}%", 
        help="You need to sell this % of your total value to make your original money back."
    )
else:
    st.sidebar.metric("Break-Even %", "N/A")

st.sidebar.divider()
st.sidebar.subheader("Manage Lots")
new_lot_name = st.sidebar.text_input("New Lot Name")
if st.sidebar.button("Create New Lot"):
    new_id = str(uuid.uuid4())
    default_name = new_lot_name if new_lot_name else f"Lot {len(st.session_state.app_data['lots']) + 1}"
    # Initialize with the new lot-level pricing keys
    st.session_state.app_data["lots"][new_id] = {
        "name": default_name, 
        "lot_market_price": 0.0,
        "lot_selling_price": 0.0,
        "cards": []
    }
    save_data(st.session_state.app_data)
    st.rerun()

# --- MAIN APP AREA ---
st.title("Pokémon Card Lot Tracker")

lot_ids = list(st.session_state.app_data["lots"].keys())

if not lot_ids:
    st.info("👈 You don't have any lots yet. Create one in the sidebar to get started!")
else:
    tabs = st.tabs([st.session_state.app_data["lots"][lid]["name"] for lid in lot_ids])
    
    for i, tab in enumerate(tabs):
        lot_id = lot_ids[i]
        lot = st.session_state.app_data["lots"][lot_id]
        
        with tab:
            col1, col2 = st.columns([3, 1])
            with col1:
                new_name = st.text_input("Rename Lot", value=lot["name"], key=f"rename_{lot_id}")
                if new_name != lot["name"]:
                    st.session_state.app_data["lots"][lot_id]["name"] = new_name
                    save_data(st.session_state.app_data)
                    st.rerun()
            with col2:
                st.write("") 
                st.write("")
                if st.button("Delete This Lot", key=f"del_{lot_id}"):
                    del st.session_state.app_data["lots"][lot_id]
                    save_data(st.session_state.app_data)
                    st.rerun()
            
            st.divider()

            # --- NEW: LOT-LEVEL PRICING ---
            st.markdown("### Bulk Lot Pricing")
            st.caption("Set a price for the entire lot if you don't want to list individual cards. These values add directly to your overall totals in the sidebar.")
            
            bulk_col1, bulk_col2 = st.columns(2)
            with bulk_col1:
                lot_market = st.number_input("Entire Lot Market Price (\$)", min_value=0.0, value=float(lot.get("lot_market_price", 0.0)), key=f"lm_{lot_id}")
            with bulk_col2:
                lot_selling = st.number_input("Entire Lot Selling Price (\$)", min_value=0.0, value=float(lot.get("lot_selling_price", 0.0)), key=f"ls_{lot_id}")
            
            st.divider()

            # --- INDIVIDUAL CARDS EDITOR ---
            st.markdown("### Individual Cards Spreadsheet")
            st.caption("Scroll to the bottom of the table to add a new card row. Edit prices directly.")
            
            df = pd.DataFrame(lot.get("cards", []))
            if df.empty:
                df = pd.DataFrame({
                    "Card Name": pd.Series(dtype='str'),
                    "Market Price": pd.Series(dtype='float'),
                    "Original Price": pd.Series(dtype='float'),
                    "Current Price": pd.Series(dtype='float'),
                    "Discount Date": pd.Series(dtype='datetime64[ns]')
                })
            else:
                df["Discount Date"] = pd.to_datetime(df["Discount Date"]).dt.date

            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_{lot_id}",
                column_config={
                    "Card Name": st.column_config.TextColumn("Card Name", required=True),
                    "Market Price": st.column_config.NumberColumn("Market Price (\$)", min_value=0.0, format="\$%.2f"),
                    "Original Price": st.column_config.NumberColumn("Original Selling Price (\$)", min_value=0.0, format="\$%.2f"),
                    "Current Price": st.column_config.NumberColumn("Current Selling Price (\$)", min_value=0.0, format="\$%.2f"),
                    "Discount Date": st.column_config.DateColumn("Discount Date")
                }
            )

            # Unified Save Button for both Bulk and Individual edits
            if st.button("Save Changes for this Lot", key=f"save_{lot_id}", type="primary"):
                # Save bulk prices
                st.session_state.app_data["lots"][lot_id]["lot_market_price"] = lot_market
                st.session_state.app_data["lots"][lot_id]["lot_selling_price"] = lot_selling
                
                # Save individual cards
                records = edited_df.to_dict('records')
                cleaned_records = []
                for r in records:
                    clean_r = {}
                    for k, v in r.items():
                        if pd.isna(v):
                            clean_r[k] = None
                        elif isinstance(v, pd.Timestamp) or hasattr(v, 'isoformat'):
                            clean_r[k] = str(v)[:10]
                        else:
                            clean_r[k] = v
                    cleaned_records.append(clean_r)
                    
                st.session_state.app_data["lots"][lot_id]["cards"] = cleaned_records
                save_data(st.session_state.app_data)
                st.success("Lot saved successfully!")
                st.rerun()
                
            st.divider()
            
            # Visual Representation & Generated Margins
            st.markdown("### Visual Representation & Margins")
            
            # Display Bulk Lot Metrics if populated
            if lot_market > 0 or lot_selling > 0:
                bulk_profit_pct = ((lot_selling - lot_market) / lot_market) * 100 if lot_market > 0 else 0.0
                st.markdown(f"**📦 BULK LOT** | Market: \${lot_market:.2f} | Selling for: **\${lot_selling:.2f}** | **Profit Margin: {bulk_profit_pct:.1f}%**")
                if not edited_df.empty and not pd.isna(edited_df.iloc[0].get("Card Name")):
                    st.caption("*Plus the following individual cards:*")
            
            # Display Individual Card Metrics
            for _, row in edited_df.iterrows():
                name = row.get("Card Name")
                if pd.isna(name) or not name:
                    continue
                    
                m_price = row.get("Market Price") if pd.notna(row.get("Market Price")) else 0.0
                o_price = row.get("Original Price") if pd.notna(row.get("Original Price")) else 0.0
                c_price = row.get("Current Price") if pd.notna(row.get("Current Price")) else 0.0
                d_date = row.get("Discount Date")
                
                if m_price > 0:
                    profit_pct = ((c_price - m_price) / m_price) * 100
                else:
                    profit_pct = 0.0
                    
                if pd.notna(d_date) and o_price > c_price:
                    price_display = f"~~\\${o_price:.2f}~~ **\\${c_price:.2f}** *(Discounted on {d_date})*"
                else:
                    price_display = f"**\\${c_price:.2f}**"
                    
                st.markdown(f"- **{name}** | Market: \${m_price:.2f} | Selling for: {price_display} | **Profit Margin: {profit_pct:.1f}%**")
