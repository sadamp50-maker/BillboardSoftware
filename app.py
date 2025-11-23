# app.py
import io
import os
import sqlite3
from io import BytesIO
from datetime import date, datetime

import pandas as pd
import streamlit as st
from PIL import Image
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

# ---------------- Settings ----------------
# ============================  TABLE FIX CSS  ============================
st.markdown("""
<style>
/* SHOW FULL COLUMN HEADER TEXT */
thead tr th {
    white-space: normal !important;
    word-wrap: break-word !important;
    text-overflow: clip !important;
    overflow-wrap: break-word !important;
}

/* DARK FULL GRID BORDER FOR ALL CELLS */
table, th, td {
    border: 2px solid black !important;
    border-collapse: collapse !important;
}

/* FIX HEADER HEIGHT */
thead th {
    height: auto !important;
}

/* FIX CELL PADDING */
th, td {
    padding: 6px !important;
}
</style>
""", unsafe_allow_html=True)
# =======================================================================

st.set_page_config(page_title="Billboard Dashboard (SQLite)", layout="wide")
DB_FILE = "billboard.db"
IMAGE_DIR = "uploaded_images"
TABLE_NAME = "billboards"
os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------- Constants ----------------
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


# ---------------- Helpers ----------------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def initialize_db():
    conn = get_conn()
    cur = conn.cursor()
    cols_sql = ", ".join([f"'{c}' TEXT" for c in COLUMNS])
    cur.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} ({cols_sql});")
    conn.commit()
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
    count = cur.fetchone()[0]
    if count == 0:
        rows = []
        for i in range(1, 51):
            row = [str(i)] + [""] * (len(COLUMNS) - 1)
            rows.append(tuple(row))
        placeholders = ", ".join(["?"] * len(COLUMNS))
        cur.executemany(f"INSERT INTO {TABLE_NAME} VALUES ({placeholders})", rows)
        conn.commit()
    conn.close()


def load_df_from_db():
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT rowid as _rowid_, * FROM {TABLE_NAME}", conn)
    conn.close()
    # ensure columns exist
    cols = ["S No."] + [c for c in COLUMNS if c != "S No."]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    # order
    df = df[["_rowid_"] + cols]
    return df


def save_row_to_db(row_dict):
    """
    row_dict keys are column names (strings). Must include 'S No.' (string/int).
    """
    conn = get_conn()
    cur = conn.cursor()
    s_no = str(row_dict.get("S No.", ""))
    cur.execute(f"SELECT rowid FROM {TABLE_NAME} WHERE \"S No.\" = ?", (s_no,))
    res = cur.fetchone()
    if res:
        rowid = res[0]
        set_parts = []
        vals = []
        for col in COLUMNS:
            # include all columns to ensure complete update
            set_parts.append(f"\"{col}\" = ?")
            vals.append(str(row_dict.get(col, "")) if row_dict.get(col, "") is not None else "")
        vals.append(rowid)
        sql = f"UPDATE {TABLE_NAME} SET {', '.join(set_parts)} WHERE rowid = ?"
        cur.execute(sql, tuple(vals))
    else:
        vals = [str(row_dict.get(col, "")) for col in COLUMNS]
        placeholders = ", ".join(["?"] * len(COLUMNS))
        cur.execute(f"INSERT INTO {TABLE_NAME} VALUES ({placeholders})", tuple(vals))
    conn.commit()
    conn.close()


def dataframe_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Billboards")
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
        if isinstance(end_date, str) and end_date.strip() == "":
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


# ---------------- Initialize DB ----------------
initialize_db()

# ---------------- Load DF ----------------
df_raw = load_df_from_db()
df_raw["_rowid_"] = df_raw["_rowid_"].astype(int)
display_df = df_raw.drop(columns=["_rowid_"]).copy()

# ---------------- Sidebar: Filters & Save ----------------
with st.sidebar:
    st.title("🔎 Filters & Actions")
    search_q = st.text_input("Search (all columns):", value="")
    client_filter = st.text_input("Client Name contains:", value="")
    payment_filter = st.selectbox("Payment Status:", options=["All"] + PAYMENT_OPTIONS, index=0)
    contract_filter = st.selectbox("Contract Status:", options=["All"] + CONTRACT_OPTIONS, index=0)

    st.markdown("---")
    st.header("💾 Save / Export")
    if st.button("Save current DB to Excel"):
        conn = get_conn()
        full_df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
        conn.close()
        excel_bytes = dataframe_to_excel_bytes(full_df)
        st.download_button("⬇️ Download Excel (.xlsx)", data=excel_bytes, file_name="Billboard_Dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")
    st.header("📌 Tips")
    st.write("- Click a row to edit details on the sidebar.") 
    st.write("- Upload images for selected row (saved to server).")
    st.write("- Balance and Days Remaining are auto-calculated.")

# ---------------- Apply filters to display_df copy ----------------
df_filtered = display_df.copy()
if search_q:
    mask = df_filtered.astype(str).apply(lambda r: r.str.contains(search_q, case=False, na=False)).any(axis=1)
    df_filtered = df_filtered[mask]
if client_filter:
    df_filtered = df_filtered[df_filtered["Client Name"].astype(str).str.contains(client_filter, case=False, na=False)]
if payment_filter != "All":
    df_filtered = df_filtered[df_filtered["Payment Status"] == payment_filter]
if contract_filter != "All":
    df_filtered = df_filtered[df_filtered["Contract Status"] == contract_filter]

# ---------------- AgGrid Dark Border CSS (target ag classes) ----------------
st.markdown(
    """
    <style>
    /* Outer wrapper */
    .ag-root-wrapper {
        border: 2px solid #0f172a !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        box-shadow: 0 6px 18px rgba(2,6,23,0.25);
    }

    /* Header cells */
    .ag-header-cell {
        border-right: 1.5px solid #0b1220 !important;
        border-bottom: 2px solid #000 !important;
        background-color: #0b1220 !important;
        color: #fff !important;
    }

    /* Center container right edge */
    .ag-center-cols-viewport {
        border-right: 2px solid #0b1220 !important;
    }

    /* Each cell: strong vertical + horizontal borders */
    .ag-cell {
        border-right: 1.5px solid #0b1220 !important;
        border-bottom: 1.5px solid #0b1220 !important;
    }

    /* make header text bold & sticky look */
    .ag-header-cell-label {
        font-weight: 700 !important;
    }

    /* remove cell selection outline default and make hover subtle */
    .ag-row:hover .ag-cell {
        background-color: rgba(10, 20, 40, 0.04) !important;
    }

    /* ensure grid center columns don't show a gap on the right */
    .ag-center-cols-container {
        box-shadow: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Configure AgGrid ----------------
gb = GridOptionsBuilder.from_dataframe(df_filtered)
gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)

# columns editable inline
inline_cols = ["Billboard ID", "Location / Address", "Billboard Size", "Client Name", "Company Name",
               "Contact Number", "Email", "Rental Duration", "Remarks / Notes", "Partner’s Share"]
for c in inline_cols:
    gb.configure_column(c, editable=True)

gb.configure_column("S No.", editable=False, pinned="left", width=80)
gb.configure_column("Rent Amount (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Advance Received (PKR)", type=["numericColumn"], editable=True)
gb.configure_column("Balance / Credit (PKR)", type=["numericColumn"], editable=False)
gb.configure_column("Payment Status", cellEditor="agSelectCellEditor",
                    cellEditorParams={"values": PAYMENT_OPTIONS}, editable=True)
gb.configure_column("Contract Status", cellEditor="agSelectCellEditor",
                    cellEditorParams={"values": CONTRACT_OPTIONS}, editable=True)

# image renderer
js_img = JsCode("""
function(params) {
    if(!params.value) return '';
    try {
        return '<a href="'+params.value+'" target="_blank"><img src="'+params.value+'" style="height:40px;border-radius:4px;"/></a>';
    } catch(e) { return params.value; }
}
""")
gb.configure_column("Billboard Image / Link", cellRenderer=js_img, editable=False, width=120)

# row style (alternate)
row_style_js = JsCode("""
function(params) {
  if (params.node.rowIndex % 2 === 0) {
    return { 'background': '#f8fafc' };
  } else {
    return { 'background': '#eef2ff' };
  }
}
""")
gridOptions = gb.build()
gridOptions["getRowStyle"] = row_style_js

# ---------------- Show AgGrid ----------------
st.title("📊 Billboard Dashboard — SQLite Backend")
st.markdown("Editable single table — select a row to edit details on the sidebar.")

response = AgGrid(
    df_filtered,
    gridOptions=gridOptions,
    enable_enterprise_modules=False,
    update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    height=540,
)

# ---------------- Handle inline edits: map back to DB ----------------
if response and response.get("data") is not None:
    edited_df = pd.DataFrame(response["data"])
    # save each edited row
    for _, r in edited_df.iterrows():
        rowdict = {}
        for col in COLUMNS:
            rowdict[col] = r.get(col, "")
        # compute balance and days
        rent = safe_float(rowdict.get("Rent Amount (PKR)", "0"))
        adv = safe_float(rowdict.get("Advance Received (PKR)", "0"))
        rowdict["Balance / Credit (PKR)"] = str(round(rent - adv, 2))
        rowdict["Days Remaining"] = str(calc_days_remaining(rowdict.get("Contract End Date", "")))
        save_row_to_db(rowdict)
    # reload display_df after inline save
    df_raw = load_df_from_db()
    df_raw["_rowid_"] = df_raw["_rowid_"].astype(int)
    display_df = df_raw.drop(columns=["_rowid_"]).copy()
    # reapply filters (so UI updates)
    df_filtered = display_df.copy()
    if search_q:
        mask = df_filtered.astype(str).apply(lambda r: r.str.contains(search_q, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]
    if client_filter:
        df_filtered = df_filtered[df_filtered["Client Name"].astype(str).str.contains(client_filter, case=False, na=False)]
    if payment_filter != "All":
        df_filtered = df_filtered[df_filtered["Payment Status"] == payment_filter]
    if contract_filter != "All":
        df_filtered = df_filtered[df_filtered["Contract Status"] == contract_filter]

# ---------------- Selection: detailed edit panel ----------------
selected = response.get("selected_rows", [])
if selected:
    sel = selected[0]
    sno = sel.get("S No.")
    st.sidebar.markdown(f"### ✏️ Edit Row S No.: {sno}")

    # load fresh full row from DB
    conn = get_conn()
    full_row = pd.read_sql_query(f"SELECT rowid, * FROM {TABLE_NAME} WHERE \"S No.\" = ?", conn, params=(str(sno),))
    conn.close()
    if not full_row.empty:
        row = full_row.iloc[0].to_dict()

        # Editable fields in sidebar
        bid = st.sidebar.text_input("Billboard ID", value=row.get("Billboard ID", ""), key="e_bid")
        loc = st.sidebar.text_input("Location / Address", value=row.get("Location / Address", ""), key="e_loc")
        size = st.sidebar.text_input("Billboard Size", value=row.get("Billboard Size", ""), key="e_size")
        client = st.sidebar.text_input("Client Name", value=row.get("Client Name", ""), key="e_client")
        company = st.sidebar.text_input("Company Name", value=row.get("Company Name", ""), key="e_company")
        contact = st.sidebar.text_input("Contact Number", value=row.get("Contact Number", ""), key="e_contact")
        email = st.sidebar.text_input("Email", value=row.get("Email", ""), key="e_email")

        # date helper
        def parse_dt_for_widget(v):
            try:
                if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
                    return date.today()
                if isinstance(v, str):
                    return pd.to_datetime(v, dayfirst=True, errors='coerce').date()
                return pd.to_datetime(v).date()
            except:
                return date.today()

        start_date = st.sidebar.date_input("Contract Start Date", value=parse_dt_for_widget(row.get("Contract Start Date", "")), key="e_start")
        end_date = st.sidebar.date_input("Contract End Date", value=parse_dt_for_widget(row.get("Contract End Date", "")), key="e_end")

        rent_val = safe_float(row.get("Rent Amount (PKR)", "0"))
        adv_val = safe_float(row.get("Advance Received (PKR)", "0"))
        rent = st.sidebar.number_input("Rent Amount (PKR)", value=rent_val, min_value=0.0, format="%.2f", key="e_rent")
        adv = st.sidebar.number_input("Advance Received (PKR)", value=adv_val, min_value=0.0, format="%.2f", key="e_adv")

        pay_status = st.sidebar.selectbox("Payment Status", options=PAYMENT_OPTIONS, index=PAYMENT_OPTIONS.index(row.get("Payment Status")) if row.get("Payment Status") in PAYMENT_OPTIONS else 1, key="e_pay")
        # ... previous code unchanged ...
# ---------- Payment, Contract status and Remarks (fixed) ----------
pay_status = st.sidebar.selectbox(
    "Payment Status",
    PAYMENT_OPTIONS,
    index=PAYMENT_OPTIONS.index(row.get("Payment Status")) if row.get("Payment Status") in PAYMENT_OPTIONS else 0,
    key=f"e_pay_{sno}",
)

contract_status = st.sidebar.selectbox(
    "Contract Status",
    CONTRACT_OPTIONS,
    index=CONTRACT_OPTIONS.index(row.get("Contract Status")) if row.get("Contract Status") in CONTRACT_OPTIONS else 0,
    key=f"e_contract_{sno}",
)

# Remarks field (added because 'remarks' is used later when saving)
remarks = st.sidebar.text_area(
    "Remarks / Notes",
    value=row.get("Remarks / Notes", ""),
    key=f"e_remarks_{sno}"
)
# ------------------------------------------------------------------

# ... rest of file unchanged ...
rent = st.sidebar.number_input("Rent", value=row.get("Rent", 0), key="e_rent")
adv = st.sidebar.number_input("Advance", value=row.get("Advance", 0), key="e_adv")

partner_share = st.sidebar.text_input(
    "Partner’s Share",
    value=row.get("Partner’s Share", ""),
    key=f"e_partner_{sno}",
)
        # image upload
st.sidebar.markdown("### 📸 Upload / Replace Image")
uploaded_file = st.sidebar.file_uploader("Choose image (png/jpg):", type=["png", "jpg", "jpeg"], key=f"img_{sno}")
        fpath = None
        if uploaded_file is not None:
            ext = os.path.splitext(uploaded_file.name)[1]
            fname = f"sno_{sno}{ext}"
            fpath = os.path.join(IMAGE_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.sidebar.success(f"Image saved: {fpath}")
            try:
                st.sidebar.image(fpath, use_column_width=True)
            except:
                st.sidebar.write("Saved image but preview failed.")

        # show existing image preview if present
        existing_img = row.get("Billboard Image / Link", "")
        if isinstance(existing_img, str) and existing_img and os.path.exists(existing_img):
            try:
                st.sidebar.image(existing_img, caption="Existing Image", use_column_width=True)
            except:
                st.sidebar.write("Image path exists but preview failed.")

        if st.sidebar.button("Apply changes"):
            new_row = {col: "" for col in COLUMNS}
            new_row["S No."] = str(sno)
            new_row["Billboard ID"] = bid
            new_row["Location / Address"] = loc
            new_row["Billboard Size"] = size
            new_row["Client Name"] = client
            new_row["Company Name"] = company
            new_row["Contact Number"] = contact
            new_row["Email"] = email
            new_row["Contract Start Date"] = str(start_date)
            new_row["Contract End Date"] = str(end_date)
            new_row["Rental Duration"] = row.get("Rental Duration", "")
            new_row["Rent Amount (PKR)"] = str(round(rent, 2))
            new_row["Advance Received (PKR)"] = str(round(adv, 2))
            new_row["Balance / Credit (PKR)"] = str(round(rent - adv, 2))
            new_row["Payment Status"] = pay_status
            new_row["Contract Status"] = contract_status
            new_row["Days Remaining"] = str(calc_days_remaining(str(end_date)))
            new_row["Remarks / Notes"] = remarks
            if fpath:
                new_row["Billboard Image / Link"] = fpath
            else:
                new_row["Billboard Image / Link"] = row.get("Billboard Image / Link", "")
            new_row["Partner’s Share"] = partner_share

            save_row_to_db(new_row)
            st.sidebar.success("Row updated and saved to database.")

            # refresh main display
            df_raw = load_df_from_db()
            df_raw["_rowid_"] = df_raw["_rowid_"].astype(int)
            display_df = df_raw.drop(columns=["_rowid_"]).copy()
            df_filtered = display_df.copy()
            if search_q:
                mask = df_filtered.astype(str).apply(lambda r: r.str.contains(search_q, case=False, na=False)).any(axis=1)
                df_filtered = df_filtered[mask]
            if client_filter:
                df_filtered = df_filtered[df_filtered["Client Name"].astype(str).str.contains(client_filter, case=False, na=False)]
            if payment_filter != "All":
                df_filtered = df_filtered[df_filtered["Payment Status"] == payment_filter]
            st.markdown("""
<style>
/* Make AgGrid column headers show full text */
.ag-header-cell-label {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    height: auto !important;
    line-height: 1.2 !important;
}

/* Allow wrapping inside header */
.ag-header-cell-text {
    white-space: normal !important;
}

/* Optional: Increase header height so wrapped text fits */
.ag-header {
    height: 70px !important;
    max-height: 120px !important;
}
</style>
""", unsafe_allow_html=True)

            if contract_filter != "All":
                df_filtered = df_filtered[df_filtered["Contract Status"] == contract_filter]

# ---------------- Show counts & export current DB ----------------
conn = get_conn()
full_df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
conn.close()

st.markdown(f"**Showing {len(df_filtered)} rows (filtered). Total rows in DB: {len(full_df)}**")

st.subheader("⬇️ Export current DB")
excel_bytes = dataframe_to_excel_bytes(full_df)
st.download_button(
"⬇️ Download Excel (.xlsx)", data=excel_bytes,
file_name="Billboard_DB.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
csv_bytes = full_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download CSV",
    data=csv_bytes,
    file_name="Billboard_DB.csv",
    mime="text/csv"
)
st.markdown("""
<style>
tbody tr td, tbody tr th {
    border: 1px solid #333 !important;   /* Dark border */
}
thead tr th {
    border: 1px solid #333 !important;   /* Header border */
}
.css-1q1n0ol { 
    border: 1px solid #333 !important;   /* Outer border */
}
</style>
""", unsafe_allow_html=True)









st.markdown(
    """
    <style>
    .ag-root-wrapper { border: 2px solid #000 !important; }
    .ag-header-cell-label { white-space: normal !important; text-overflow: clip !important; overflow: visible !important; }
    .ag-cell, .ag-header-cell { border: 1px solid black !important; }
    .ag-header { border-bottom: 2px solid black !important; }
    .ag-center-cols-container { border-right: 2px solid black !important; }
    </style>
    """, unsafe_allow_html=True)






