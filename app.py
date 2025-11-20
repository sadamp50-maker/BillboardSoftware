import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from io import BytesIO
import io
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
            for col in COLUMNS:
                if col not in d.columns:
                    d[col] = ""
            d = d[COLUMNS]
            return d
        except:
            pass

    df0 = pd.DataFrame({col: [""] * 50 for col in COLUMNS})
    df0["S No."] = range(1, 51)
    df0["Payment Status"] = "Unpaid"
    df0["Contract Status"] = "Pending"
    return df0

def save_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dashboard")
    return output.getvalue()

def safe_float(x):
    try:
        if pd.isna(x) or x == "":
            return 0.0
        return float(str(x).replace(",", "").strip())
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
        return int((end.date() - date.today()).days)
    except:
        return ""

# ---------- Load ----------
if "df" not in st.session_state:
    st.session_state.df = load_initial_df()
    st.session_state.df["S No."] = st.session_state.df["S No."].astype(int)

df = st.session_state.df.copy()

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🔎 Filters & Actions")
    search_q = st.text_input("Search:", "")
    client_filter = st.text_input("Client Name contains:", "")
    payment_filter = st.selectbox("Payment Status:", ["All"] + PAYMENT_OPTIONS)
    contract_filter = st.selectbox("Contract Status:", ["All"] + CONTRACT_OPTIONS)

    st.markdown("---")
    st.header("📁 Save / Export")
    if st.button("💾 Save"):
        excel_bytes = save_df_to_excel(st.session_state.df)
        st.success("Saved Successfully!")
        st.download_button("⬇️ Download File", data=excel_bytes, file_name=DATA_FILE)

    st.markdown("---")
    st.header("📌 Tips")
    st.write("""
- Click a row to edit  
- Upload image for selected row  
- Balance & Days Remaining auto update  
""")

# ---------- Filters ----------
display_df = df.copy()

if search_q:
    mask = display_df.astype(str).apply(lambda r: r.str.contains(search_q, case=False, na=False)).any(axis=1)
    display_df = display_df[mask]

if client_filter:
    display_df = display_df[display_df["Client Name"].astype(str).str.contains(client_filter, case=False, na=False)]

if payment_filter != "All":
    display_df = display_df[display_df["Payment Status"] == payment_filter]

if contract_filter != "All":
    display_df = display_df[display_df["Contract Status"] == contract_filter]

# ---------- AgGrid Setup ----------
gb = GridOptionsBuilder.from_dataframe(display_df)
gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)

editable_cols = [
    "Billboard ID", "Location / Address", "Billboard Size", "Client Name", "Company Name",
    "Contact Number", "Email", "Rental Duration", "Remarks / Notes", "Partner’s Share"
]
for c in editable_cols:
    gb.configure_column(c, editable=True)

gb.configure_column("S No.", editable=False, pinned="left", width=80)

gb.configure_column("Rent Amount (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Advance Received (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Balance / Credit (PKR)", type=["numericColumn"], editable=False)

gb.configure_column("Payment Status", cellEditor="agSelectCellEditor",
                    cellEditorParams={"values": PAYMENT_OPTIONS}, editable=True)

gb.configure_column("Contract Status", cellEditor="agSelectCellEditor",
                    cellEditorParams={"values": CONTRACT_OPTIONS}, editable=True)

# Image thumbnail
js_img = JsCode("""
function(params){
 if(!params.value) return '';
 return `<a href="${params.value}" target="_blank">
 <img src="${params.value}" style="height:40px;border-radius:4px;"/>
 </a>`;
}
""")
gb.configure_column("Billboard Image / Link", cellRenderer=js_img, editable=False, width=110)

# Row alternate colors
row_style_js = JsCode("""
function(params){
 if(params.node.rowIndex % 2 === 0){ return {'background':'#dbe4ff'}; }
 else{ return {'background':'#e8dbff'}; }
}
""")

gridOptions = gb.build()
gridOptions["getRowStyle"] = row_style_js

# ---------- Display Table ----------
st.header("🗂️ Billboard Table")
response = AgGrid(
    display_df,
    gridOptions=gridOptions,
    update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    height=520
)

# ---------- Update df after inline edits ----------
if response and response.get("data") is not None:
    edited_df = pd.DataFrame(response["data"])
    full = st.session_state.df.copy()

    for _, r in edited_df.iterrows():
        sn = int(r["S No."])
        idx = full.index[full["S No."] == sn].tolist()
        if not idx:
            continue
        i = idx[0]
        for col in edited_df.columns:
            if col in COLUMNS:
                full.at[i, col] = r[col]

    st.session_state.df = full

# ---------- Edit selected row ----------
selected = response.get("selected_rows", [])
if selected:
    sel = selected[0]
    sno = int(sel["S No."])

    st.sidebar.markdown(f"### ✏️ Editing Row {sno}")

    full = st.session_state.df.copy()
    idx = full.index[full["S No."] == sno].tolist()[0]

    st.sidebar.text_input("Billboard ID", full.at[idx, "Billboard ID"], key="e_bid")
    st.sidebar.text_input("Location / Address", full.at[idx, "Location / Address"], key="e_loc")
    st.sidebar.text_input("Billboard Size", full.at[idx, "Billboard Size"], key="e_size")
    st.sidebar.text_input("Client Name", full.at[idx, "Client Name"], key="e_client")
    st.sidebar.text_input("Company Name", full.at[idx, "Company Name"], key="e_company")
    st.sidebar.text_input("Contact Number", full.at[idx, "Contact Number"], key="e_contact")
    st.sidebar.text_input("Email", full.at[idx, "Email"], key="e_email")

    # Dates
    def parse_dt(val):
        try:
            if pd.isna(val) or val == "":
                return date.today()
            if isinstance(val, pd.Timestamp):
                return val.date()
            return pd.to_datetime(val, dayfirst=True).date()
        except:
            return date.today()

    start_date = st.sidebar.date_input("Contract Start Date", parse_dt(full.at[idx, "Contract Start Date"]), key="e_start")
    end_date = st.sidebar.date_input("Contract End Date", parse_dt(full.at[idx, "Contract End Date"]), key="e_end")

    rent = st.sidebar.number_input("Rent Amount", safe_float(full.at[idx, "Rent Amount (PKR)"]), min_value=0.0, key="e_rent")
    adv = st.sidebar.number_input("Advance Received", safe_float(full.at[idx, "Advance Received (PKR)"]), min_value=0.0, key="e_adv")

    pay_status = st.sidebar.selectbox("Payment Status", PAYMENT_OPTIONS, key="e_pay")
    contract_status = st.sidebar.selectbox("Contract Status", CONTRACT_OPTIONS, key="e_contract")

    remarks = st.sidebar.text_area("Remarks", full.at[idx, "Remarks / Notes"], key="e_rem")
    partner_share = st.sidebar.text_input("Partner’s Share", full.at[idx, "Partner’s Share"], key="e_partner")

    # ---------- Image Upload ----------
    st.sidebar.markdown("### 📸 Upload Image")
    uploaded_image = st.sidebar.file_uploader("Upload Billboard Image", type=["jpg", "jpeg", "png"])

    if uploaded_image:
        img_name = f"billboard_{sno}_{uploaded_image.name}"
        img_path = os.path.join(IMAGE_DIR, img_name)

        with open(img_path, "wb") as f:
            f.write(uploaded_image.getbuffer())

        full.at[idx, "Billboard Image / Link"] = img_path
        st.session_state.df = full
        st.sidebar.success("Image Saved!")

        st.sidebar.image(img_path, width=200)

