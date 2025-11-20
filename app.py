import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from io import BytesIO
from datetime import datetime, date
from PIL import Image

# ---------- Settings ----------
st.set_page_config(page_title="Billboard Dashboard — Full", layout="wide")
DATA_FILE = "Billboard_Dashboard_autosave.xlsx"
IMAGE_DIR = "uploaded_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------- Constants ----------
PAYMENT_OPTIONS = ["Paid", "Unpaid", "Partial"]
CONTRACT_OPTIONS = ["Active", "Expired", "Pending"]

COLUMNS = [
    "S No.", "Billboard ID", "Location / Address", "Billboard Size",
    "Client Name", "Company Name", "Contact Number", "Email",
    "Contract Start Date", "Contract End Date", "Rental Duration",
    "Rent Amount (PKR)", "Advance Received (PKR)", "Balance / Credit (PKR)",
    "Payment Status", "Contract Status", "Days Remaining",
    "Remarks / Notes", "Billboard Image / Link", "Partner’s Share"
]

# ---------- Helpers ----------
def load_initial_df():
    if os.path.exists(DATA_FILE):
        try:
            d = pd.read_excel(DATA_FILE, engine="openpyxl")
            # Ensure columns exist
            for col in COLUMNS:
                if col not in d.columns:
                    d[col] = ""
            d = d[COLUMNS]
            return d
        except Exception:
            pass
    # default new DF
    df0 = pd.DataFrame({col: [""] * 50 for col in COLUMNS})
    df0["S No."] = range(1, 51)
    df0["Payment Status"] = "Unpaid"
    df0["Contract Status"] = "Pending"
    return df0

def save_df_to_excel(df):
    with BytesIO() as buffer:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Billboards")
            writer.save()
        data = buffer.getvalue()
    # save a copy to disk for autosave
    with open(DATA_FILE, "wb") as f:
        f.write(data)
    return data

def safe_float(x):
    try:
        if pd.isna(x) or x == "":
            return 0.0
        s = str(x).replace(",", "").strip()
        return float(s)
    except:
        return 0.0

def calc_days_remaining(end_date):
    try:
        if pd.isna(end_date) or end_date == "":
            return ""
        if isinstance(end_date, str):
            end = pd.to_datetime(end_date, dayfirst=True, errors='coerce')
        else:
            end = pd.to_datetime(end_date)
        if pd.isna(end):
            return ""
        delta = (end.date() - date.today()).days
        return int(delta)
    except:
        return ""

# ---------- Load / Session State ----------
if "df" not in st.session_state:
    st.session_state.df = load_initial_df()
    # ensure types
    st.session_state.df["S No."] = st.session_state.df["S No."].astype(int)

df = st.session_state.df.copy()

# ---------- Sidebar: Search / Filters / Upload ----------
with st.sidebar:
    st.title("🔎 Filters & Actions")
    search_q = st.text_input("Search (all columns):", value="")
    client_filter = st.text_input("Client Name contains:", value="")
    payment_filter = st.selectbox("Payment Status:", options=["All"] + PAYMENT_OPTIONS, index=0)
    contract_filter = st.selectbox("Contract Status:", options=["All"] + CONTRACT_OPTIONS, index=0)
    st.markdown("---")
    st.header("📁 Save / Export")
    if st.button("💾 Save (autosave + file)"):
        excel_bytes = save_df_to_excel(st.session_state.df)
        st.success("Saved to " + DATA_FILE)
        st.download_button("⬇️ Download saved Excel", data=excel_bytes, file_name=DATA_FILE, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("---")
    st.header("📌 Tips")
    st.write("""
- Select a row in table to edit detailed fields below.
- Use numeric fields for Rent/Advance (commas allowed).
- Upload images per selected row (they will be saved to `uploaded_images/`).
- Balance and Days Remaining calculate automatically.
""")

# ---------- Prepare display_df with filters ----------
display_df = df.copy()

# apply global search
if search_q:
    mask = display_df.astype(str).apply(lambda row: row.str.contains(search_q, case=False, na=False)).any(axis=1)
    display_df = display_df[mask]

if client_filter:
    display_df = display_df[display_df["Client Name"].astype(str).str.contains(client_filter, case=False, na=False)]

if payment_filter != "All":
    display_df = display_df[display_df["Payment Status"] == payment_filter]

if contract_filter != "All":
    display_df = display_df[display_df["Contract Status"] == contract_filter]

# ---------- Configure AgGrid ----------
gb = GridOptionsBuilder.from_dataframe(display_df)
gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)
# allow editing in-grid for some columns (basic inline edits)
editable_cols = ["Billboard ID", "Location / Address", "Billboard Size", "Client Name", "Company Name",
                 "Contact Number", "Email", "Rental Duration", "Remarks / Notes", "Partner’s Share"]
for c in editable_cols:
    gb.configure_column(c, editable=True)

gb.configure_column("S No.", editable=False, pinned="left", width=80)
gb.configure_column("Rent Amount (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Advance Received (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Balance / Credit (PKR)", type=["numericColumn"], editable=False)
gb.configure_column("Payment Status", cellEditor="agSelectCellEditor", cellEditorParams={"values": PAYMENT_OPTIONS}, editable=True)
gb.configure_column("Contract Status", cellEditor="agSelectCellEditor", cellEditorParams={"values": CONTRACT_OPTIONS}, editable=True)

# image renderer (show small thumbnail if path present)
js_img = JsCode("""
function(params) {
  if(!params.value) return '';
  let v = params.value;
  // if looks like local path, create relative src
  return `<a href="${v}" target="_blank"><img src="${v}" style="height:40px;border-radius:4px;"/></a>`;
}
""")
gb.configure_column("Billboard Image / Link", cellRenderer=js_img, editable=False, width=100)

# row colors
row_style_js = JsCode("""
function(params) {
  if (params.node.rowIndex % 2 === 0) {
    return { 'background': '#e0e8ff' };
  } else {
    return { 'background': '#f0e8ff' };
  }
}
""")
gridOptions = gb.build()
gridOptions["getRowStyle"] = row_style_js

# ---------- Show AgGrid (single editable colored table) ----------
st.header("🗂️ Billboard Table (Click a row to edit details)")
response = AgGrid(
    display_df,
    gridOptions=gridOptions,
    enable_enterprise_modules=False,
    update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.MODEL_CHANGED,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    height=520,
)

# when user edits inline cells, update master df
if response and response.get("data") is not None:
    edited_display_df = pd.DataFrame(response["data"])
    # Map back edits to session_state.df using S No.
    full = st.session_state.df.copy()
    for _, r in edited_display_df.iterrows():
        try:
            sn = int(r["S No."])
        except:
            continue
        idx = full.index[full["S No."] == sn].tolist()
        if not idx:
            continue
        i = idx[0]
        for col in edited_display_df.columns:
            if col in COLUMNS:
                # update only editable columns and those present
                full.at[i, col] = r[col]
    st.session_state.df = full

# ---------- Selection handling: edit selected row with proper widgets ----------
selected = response.get("selected_rows", [])
if selected:
    sel = selected[0]  # single selection
    sno = int(sel["S No."])
    st.sidebar.markdown(f"### ✏️ Editing Row S No.: {sno}")
    # find index in full df
    full = st.session_state.df.copy()
    idx = full.index[full["S No."] == sno].tolist()[0]

    # fields for edit (use proper widgets)
    st.sidebar.text_input("Billboard ID", value=str(full.at[idx, "Billboard ID"]), key="e_billboard_id")
    st.sidebar.text_input("Location / Address", value=str(full.at[idx, "Location / Address"]), key="e_location")
    st.sidebar.text_input("Billboard Size", value=str(full.at[idx, "Billboard Size"]), key="e_size")
    st.sidebar.text_input("Client Name", value=str(full.at[idx, "Client Name"]), key="e_client")
    st.sidebar.text_input("Company Name", value=str(full.at[idx, "Company Name"]), key="e_company")
    st.sidebar.text_input("Contact Number", value=str(full.at[idx, "Contact Number"]), key="e_contact")
    st.sidebar.text_input("Email", value=str(full.at[idx, "Email"]), key="e_email")

    # Dates
    # parse existing date safely
    def parse_dt(val):
        try:
            if pd.isna(val) or val == "":
                return None
            if isinstance(val, pd.Timestamp):
                return val.date()
            # try parse string
            return pd.to_datetime(val, dayfirst=True).date()
        except:
            return None

    start_val = parse_dt(full.at[idx, "Contract Start Date"])
    end_val = parse_dt(full.at[idx, "Contract End Date"])
    start_date = st.sidebar.date_input("Contract Start Date", value=start_val if start_val else date.today(), key="e_start")
    end_date = st.sidebar.date_input("Contract End Date", value=end_val if end_val else date.today(), key="e_end")

    # numeric fields with validation
    rent_val = safe_float(full.at[idx, "Rent Amount (PKR)"])
    adv_val = safe_float(full.at[idx, "Advance Received (PKR)"])
    rent = st.sidebar.number_input("Rent Amount (PKR)", value=rent_val, min_value=0.0, format="%.2f", key="e_rent")
    adv = st.sidebar.number_input("Advance Received (PKR)", value=adv_val, min_value=0.0, format="%.2f", key="e_adv")

    # dropdowns
    pay_status = st.sidebar.selectbox("Payment Status", options=PAYMENT_OPTIONS, index=PAYMENT_OPTIONS.index(full.at[idx, "Payment Status"]) if full.at[idx, "Payment Status"] in PAYMENT_OPTIONS else 1, key="e_pay")
    contract_status = st.sidebar.selectbox("Contract Status", options=CONTRACT_OPTIONS, index=CONTRACT_OPTIONS.index(full.at[idx, "Contract Status"]) if full.at[idx, "Contract Status"] in CONTRACT_OPTIONS else 2, key="e_contract")

    remarks = st.sidebar.text_area("Remarks / Notes", value=str(full.at[idx, "Remarks / Notes"]), key="e_remarks")
    partner_share = st.sidebar.text_input("Partner’s Share", value=str(full.at[idx, "Partner’s Share"]), key="e_partner")

    # Image upload for this selected S No.
    st.sidebar.markdown("**Upload / Replace Billboard Image**")
    uploaded_file = st.sidebar.file_uploader("Choose image (png/jpg):", type=["png", "jpg", "jpeg"], key=f"img_{sno}")
  if uploaded_image is not None:
    img_name = uploaded_image.name
    fpath = os.path.join("images", img_name)
    with open(fpath, "wb") as f:
        f.write(uploaded_image.getbuffer())

    st.sidebar.success(f"Image saved: {fpath}")


