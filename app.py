import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from io import BytesIO

st.set_page_config(page_title="Billboard Dashboard (Pro)", layout="wide")

# ---------- Constants / Dropdown options ----------
PAYMENT_OPTIONS = ["Paid", "Unpaid", "Partial"]
CONTRACT_OPTIONS = ["Active", "Expired", "Pending"]

# ---------- Columns ----------
columns = [
    "S No.", "Billboard ID", "Location / Address", "Billboard Size",
    "Client Name", "Company Name", "Contact Number", "Email",
    "Contract Start Date", "Contract End Date", "Rental Duration",
    "Rent Amount (PKR)", "Advance Received (PKR)", "Balance / Credit (PKR)",
    "Payment Status", "Contract Status", "Days Remaining",
    "Remarks / Notes", "Billboard Image / Link", "Partner’s Share"
]

# ---------- Initial DF (50 rows) ----------
if "df" not in st.session_state:
    df = pd.DataFrame({col: [""] * 50 for col in columns})
    df["S No."] = range(1, 51)
    # set default dropdown values
    df["Payment Status"] = "Unpaid"
    df["Contract Status"] = "Pending"
    df["Rent Amount (PKR)"] = ""
    df["Advance Received (PKR)"] = ""
    df["Balance / Credit (PKR)"] = ""
    st.session_state.df = df
else:
    df = st.session_state.df

st.title("📊 Billboard Management Dashboard — Pro")
st.markdown("Editable single table (colored) — search, dropdowns, auto-balance, and export.")

# ---------- Search / Filters ----------
with st.sidebar:
    st.header("🔎 Search / Filters")
    q = st.text_input("Search (all columns):", value="")
    client_filter = st.text_input("Filter Client Name (contains):", value="")
    payment_filter = st.selectbox("Filter Payment Status:", options=["All"] + PAYMENT_OPTIONS, index=0)
    contract_filter = st.selectbox("Filter Contract Status:", options=["All"] + CONTRACT_OPTIONS, index=0)
    st.markdown("---")
    st.markdown("💾 Use Export buttons below to download current table.")

# apply search/filter on a copy for display (keeps session_state.df intact)
display_df = df.copy()

# global search across all string columns
if q:
    mask = display_df.astype(str).apply(lambda row: row.str.contains(q, case=False, na=False)).any(axis=1)
    display_df = display_df[mask]

if client_filter:
    display_df = display_df[display_df["Client Name"].astype(str).str.contains(client_filter, case=False, na=False)]

if payment_filter != "All":
    display_df = display_df[display_df["Payment Status"] == payment_filter]

if contract_filter != "All":
    display_df = display_df[display_df["Contract Status"] == contract_filter]

# ---------- Configure AgGrid ----------
gb = GridOptionsBuilder.from_dataframe(display_df)
gb.configure_default_column(editable=True, resizable=True, filter=True, sortable=True)

# Dropdown editors for specific columns
gb.configure_column("Payment Status", cellEditor="agSelectCellEditor", cellEditorParams={"values": PAYMENT_OPTIONS}, editable=True)
gb.configure_column("Contract Status", cellEditor="agSelectCellEditor", cellEditorParams={"values": CONTRACT_OPTIONS}, editable=True)

# Make S No. non-editable
gb.configure_column("S No.", editable=False, pinned="left", width=70)

# Make numeric columns accept numeric entry (text still ok but we'll coerce later)
gb.configure_column("Rent Amount (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Advance Received (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Balance / Credit (PKR)", type=["numericColumn"], editable=False)

# Render image link as clickable (simple renderer)
js_link = JsCode("""
function(params) {
    if(!params.value) return '';
    return '<a href="' + params.value + '" target="_blank">View</a>';
}
""")
gb.configure_column("Billboard Image / Link", cellRenderer=js_link, editable=True)

# Row styling: alternate row colors + header style via gridStyle
# Use getRowStyle JS to set background color by row index
row_style_js = JsCode("""
function(params) {
  if (params.node.rowIndex % 2 === 0) {
    return { 'background': '#e0e8ff' }; // medium blue tint
  } else {
    return { 'background': '#f0e8ff' }; // medium lavender tint
  }
}
""")
gridOptions = gb.build()
gridOptions["getRowStyle"] = row_style_js

# header style via gridOptions (uses CSS injection below)
gridHeight = 600

# ---------- Show AgGrid ----------
st.subheader("Editable Table")
response = AgGrid(
    display_df,
    gridOptions=gridOptions,
    enable_enterprise_modules=False,
    update_mode=GridUpdateMode.MODEL_CHANGED,
    fit_columns_on_grid_load=True,
    height=gridHeight,
    allow_unsafe_jscode=True,
)

# ---------- When grid changes, update session_state.df ----------
# response['data'] is the currently visible (and edited) slice — it may be filtered.
edited_display_df = pd.DataFrame(response["data"])

# We need to map edited_display_df back into full st.session_state.df by index (S No.)
# We'll use S No. as key; ensure it's present and numeric
try:
    edited_display_df["S No."] = edited_display_df["S No."].astype(int)
except Exception:
    # fallback: use current index mapping
    pass

# update rows in st.session_state.df where S No. matches
full_df = st.session_state.df.copy()
for _, row in edited_display_df.iterrows():
    sn = int(row["S No."])
    # find location in full_df (S No. is unique and 1..50)
    idx = full_df.index[full_df["S No."] == sn].tolist()
    if idx:
        i = idx[0]
        for col in columns:
            # only update if column exists in edited row (it should)
            if col in edited_display_df.columns:
                full_df.at[i, col] = row[col]

# ---------- Auto Balance Calculation ----------
def safe_to_float(x):
    try:
        if x is None or x == "":
            return 0.0
        # remove commas and spaces
        s = str(x).replace(",", "").strip()
        return float(s)
    except:
        return 0.0

for i in full_df.index:
    rent = safe_to_float(full_df.at[i, "Rent Amount (PKR)"])
    adv = safe_to_float(full_df.at[i, "Advance Received (PKR)"])
    balance = rent - adv
    # round to 2 decimals
    full_df.at[i, "Balance / Credit (PKR)"] = round(balance, 2)

# store back to session_state
st.session_state.df = full_df

# show info
st.markdown(f"Showing **{len(display_df)}** rows (filtered from {len(full_df)} total).")

# ---------- EXPORT / DOWNLOAD ----------
st.subheader("Export / Save")
export_cols = st.multiselect("Choose columns to export (leave all to export whole table):", options=columns, default=columns)

export_df = st.session_state.df[export_cols].copy()

# Excel export
def to_excel_bytes(df_in: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_in.to_excel(writer, index=False, sheet_name="Billboard")
        writer.save()
    return buffer.getvalue()

excel_bytes = to_excel_bytes(export_df)
st.download_button("⬇️ Download Excel (.xlsx)", data=excel_bytes, file_name="Billboard_Dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# CSV export
csv_bytes = export_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download CSV", data=csv_bytes, file_name="Billboard_Dashboard.csv", mime="text/csv")

# ---------- Small UI tips ----------
st.markdown("---")
st.write("Tips:")
st.markdown("- **Click any cell** to edit. S No. is locked (non-editable).")
st.markdown("- **Payment Status** and **Contract Status** use dropdown choices.")
st.markdown("- Enter numeric values in Rent / Advance (commas allowed). Balance recalculates automatically.")
st.markdown("- Use the search box on the left to filter across all columns.")
