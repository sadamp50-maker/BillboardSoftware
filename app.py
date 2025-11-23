
# app_fixed.py
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
    cols = ["S No."] + [c for c in COLUMNS if c != "S No."]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[["_rowid_"] + cols]
    return df

def save_row_to_db(row_dict):
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

# ---------------- Sidebar: Filters & Export ----------------
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
        st.download_button("⬇️ Download Excel (.xlsx)", data=excel_bytes,
                           file_name="Billboard_Dashboard.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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

# ---------------- Configure AgGrid ----------------
gb = GridOptionsBuilder.from_dataframe(df_filtered)
gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)
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

js_img = JsCode("""
function(params) {
    if(!params.value) return '';
    try {
        return '<a href="'+params.value+'" target="_blank"><img src="'+params.value+'" style="height:40px;border-radius:4px;"/></a>';
    } catch(e) { return params.value; }
}
""")

\""")
gb.configure_column("Billboard Image / Link", cellRenderer=js_img, editable=False, width=120)

row_style_js = JsCode(\"\"\"
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
    for _, r in edited_df.iterrows():
        rowdict = {}
        for col in COLUMNS:
            rowdict[col] = r.get(col, "")
        rent = safe_float(rowdict.get("Rent Amount (PKR)", "0"))
        adv = safe_float(rowdict.get("Advance Received (PKR)", "0"))
        rowdict["Balance / Credit (PKR)"] = str(round(rent - adv, 2))
        rowdict["Days Remaining"] = str(calc_days_remaining(rowdict.get("Contract End Date", "")))
        save_row_to_db(rowdict)
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
    if contract_filter != "All":
        df_filtered = df_filtered[df_filtered["Contract Status"] == contract_filter]

# ---------------- Selection: detailed edit panel (session-state stable) ----------------
selected = response.get("selected_rows", [])
if selected:
    sel = selected[0]
    sno = sel.get("S No.")
    st.sidebar.markdown(f"### ✏️ Edit Row S No.: {sno}")

    conn = get_conn()
    full_row = pd.read_sql_query(f"SELECT rowid, * FROM {TABLE_NAME} WHERE \"S No.\" = ?", conn, params=(str(sno),))
    conn.close()
    if not full_row.empty:
        row = full_row.iloc[0].to_dict()

        # ensure session_state keys for this sno are initialized once per selection
        def init_state(k, v):
            if k not in st.session_state:
                st.session_state[k] = v

        init_state(f"bid_{sno}", row.get("Billboard ID", ""))
        init_state(f"loc_{sno}", row.get("Location / Address", ""))
        init_state(f"size_{sno}", row.get("Billboard Size", ""))
        init_state(f"client_{sno}", row.get("Client Name", ""))
        init_state(f"company_{sno}", row.get("company_{sno}", ""))
        init_state(f"contact_{sno}", row.get("Contact Number", ""))
        init_state(f"email_{sno}", row.get("Email", ""))
        init_state(f"start_{sno}", row.get("Contract Start Date", str(date.today())))
        init_state(f"end_{sno}", row.get("Contract End Date", str(date.today())))
        init_state(f"rent_{sno}", safe_float(row.get("Rent Amount (PKR)", "0")))
        init_state(f"adv_{sno}", safe_float(row.get("Advance Received (PKR)", "0")))
        init_state(f"pay_{sno}", row.get("Payment Status", PAYMENT_OPTIONS[0]))
        init_state(f"contract_{sno}", row.get("Contract Status", CONTRACT_OPTIONS[0]))
        init_state(f"remarks_{sno}", row.get("Remarks / Notes", ""))
        init_state(f"partner_{sno}", row.get("Partner’s Share", ""))
        init_state(f"imgpath_{sno}", row.get("Billboard Image / Link", ""))

        # Sidebar inputs bind to session_state keys (prevents losing typed text on rerun)
        bid = st.sidebar.text_input("Billboard ID", key=f"bid_{sno}")
        loc = st.sidebar.text_input("Location / Address", key=f"loc_{sno}")
        size = st.sidebar.text_input("Billboard Size", key=f"size_{sno}")
        client = st.sidebar.text_input("Client Name", key=f"client_{sno}")
        company = st.sidebar.text_input("Company Name", key=f"company_{sno}")
        contact = st.sidebar.text_input("Contact Number", key=f"contact_{sno}")
        email = st.sidebar.text_input("Email", key=f"email_{sno}")

        # date inputs
        def parse_dt_for_widget(v):
            try:
                if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
                    return date.today()
                if isinstance(v, str):
                    return pd.to_datetime(v, dayfirst=True, errors='coerce').date()
                return pd.to_datetime(v).date()
            except:
                return date.today()

        start_date = st.sidebar.date_input("Contract Start Date", value=parse_dt_for_widget(st.session_state[f"start_{sno}"]), key=f"start_{sno}")
        end_date = st.sidebar.date_input("Contract End Date", value=parse_dt_for_widget(st.session_state[f"end_{sno}"]), key=f"end_{sno}")

        rent = st.sidebar.number_input("Rent Amount (PKR)", value=st.session_state[f"rent_{sno}"], min_value=0.0, format="%.2f", key=f"rent_{sno}")
        adv = st.sidebar.number_input("Advance Received (PKR)", value=st.session_state[f"adv_{sno}"], min_value=0.0, format="%.2f", key=f"adv_{sno}")

        pay_status = st.sidebar.selectbox("Payment Status", PAYMENT_OPTIONS, index=PAYMENT_OPTIONS.index(st.session_state[f"pay_{sno}"]) if st.session_state[f"pay_{sno}"] in PAYMENT_OPTIONS else 0, key=f"pay_{sno}")
        contract_status = st.sidebar.selectbox("Contract Status", CONTRACT_OPTIONS, index=CONTRACT_OPTIONS.index(st.session_state[f"contract_{sno}"]) if st.session_state[f"contract_{sno}"] in CONTRACT_OPTIONS else 0, key=f"contract_{sno}")

        remarks = st.sidebar.text_area("Remarks / Notes", value=st.session_state[f"remarks_{sno}"], key=f"remarks_{sno}")
        partner_share = st.sidebar.text_input("Partner’s Share", value=st.session_state[f"partner_{sno}"], key=f"partner_{sno}")

        st.sidebar.markdown("### 📸 Upload / Replace Image")
        uploaded_file = st.sidebar.file_uploader("Choose image (png/jpg):", type=["png", "jpg", "jpeg"], key=f"img_{sno}")

        fpath = st.session_state.get(f"imgpath_{sno}", "")

        if uploaded_file is not None:
            ext = os.path.splitext(uploaded_file.name)[1]
            fname = f"sno_{sno}{ext}"
            fpath = os.path.join(IMAGE_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state[f"imgpath_{sno}"] = fpath
            st.sidebar.success(f"Image saved: {fpath}")
            try:
                st.sidebar.image(fpath, use_column_width=True)
            except:
                st.sidebar.write("Saved image but preview failed.")
        else:
            if fpath and os.path.exists(fpath):
                try:
                    st.sidebar.image(fpath, caption="Existing Image", use_column_width=True)
                except:
                    st.sidebar.write("Image path exists but preview failed.")

        # Apply changes only on button click (Option B)
        if st.sidebar.button("Apply changes"):
            new_row = {col: "" for col in COLUMNS}
            new_row["S No."] = str(sno)
            new_row["Billboard ID"] = st.session_state.get(f"bid_{sno}", "")
            new_row["Location / Address"] = st.session_state.get(f"loc_{sno}", "")
            new_row["Billboard Size"] = st.session_state.get(f"size_{sno}", "")
            new_row["Client Name"] = st.session_state.get(f"client_{sno}", "")
            new_row["Company Name"] = st.session_state.get(f"company_{sno}", "")
            new_row["Contact Number"] = st.session_state.get(f"contact_{sno}", "")
            new_row["Email"] = st.session_state.get(f"email_{sno}", "")
            new_row["Contract Start Date"] = str(st.session_state.get(f"start_{sno}", start_date))
            new_row["Contract End Date"] = str(st.session_state.get(f"end_{sno}", end_date))
            new_row["Rental Duration"] = row.get("Rental Duration", "")
            new_row["Rent Amount (PKR)"] = str(round(float(st.session_state.get(f"rent_{sno}", rent)), 2))
            new_row["Advance Received (PKR)"] = str(round(float(st.session_state.get(f"adv_{sno}", adv)), 2))
            new_row["Balance / Credit (PKR)"] = str(round(float(st.session_state.get(f"rent_{sno}", rent)) - float(st.session_state.get(f"adv_{sno}", adv)), 2))
            new_row["Payment Status"] = st.session_state.get(f"pay_{sno}", pay_status)
            new_row["Contract Status"] = st.session_state.get(f"contract_{sno}", contract_status)
            new_row["Days Remaining"] = str(calc_days_remaining(str(new_row["Contract End Date"])))
            new_row["Remarks / Notes"] = st.session_state.get(f"remarks_{sno}", "")
            new_row["Partner’s Share"] = st.session_state.get(f"partner_{sno}", "")
            new_row["Billboard Image / Link"] = st.session_state.get(f"imgpath_{sno}", row.get("Billboard Image / Link", ""))

            save_row_to_db(new_row)
            st.sidebar.success("Row updated and saved to database.")

            # refresh main display: reload the dataframe and reset display_df / filters
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
            if contract_filter != "All":
                df_filtered = df_filtered[df_filtered["Contract Status"] == contract_filter]

# ---------------- Show counts & export current DB ----------------
conn = get_conn()
full_df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
conn.close()

st.markdown(f"**Showing {len(df_filtered)} rows (filtered). Total rows in DB: {len(full_df)}**")

st.subheader("⬇️ Export current DB")
excel_bytes = dataframe_to_excel_bytes(full_df)
st.download_button("⬇️ Download Excel (.xlsx)", data=excel_bytes, file_name="Billboard_DB.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
csv_bytes = full_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download CSV",
    data=csv_bytes,
    file_name="Billboard_DB.csv",
    mime="text/csv"
)


