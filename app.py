import streamlit as st
import sqlite3
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

st.set_page_config(layout="wide")

# =======================
#  🔲 CLEAR BORDER CSS
# =======================
st.markdown("""
<style>
.ag-theme-material .ag-cell {
    border-right: 1px solid #000 !important;
    border-bottom: 1px solid #000 !important;
}

.ag-theme-material .ag-header-cell {
    border-right: 1px solid #000 !important;
    border-bottom: 1px solid #000 !important;
}

.ag-theme-material .ag-row {
    border-bottom: 1px solid #000 !important;
}
</style>
""", unsafe_allow_html=True)

# =======================
#  DATABASE
# =======================
def get_db_connection():
    conn = sqlite3.connect("complaints.db")
    return conn

def initialize_db():
    conn = get_db_connection()
    conn.execute("""
       CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, phone TEXT, email TEXT,
            info TEXT, timeframe TEXT, date TEXT,
            box_number TEXT, family_members TEXT,
            calculation_result TEXT, cheque_file TEXT,
            id_picture TEXT, signature TEXT,
            picture TEXT, video_file TEXT,
            application TEXT
        )
    """)
    conn.commit()
    conn.close()

initialize_db()

# =======================
#  LOAD DATA
# =======================
def load_table_data(table_name):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

table_name = "complaints"

st.header("📊 Complaint Dashboard (Clear Borders Enabled)")
df = load_table_data(table_name)

# =======================
#  BUILD GRID
# =======================
gb = GridOptionsBuilder.from_dataframe(df)

gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=10)
gb.configure_selection('multiple', use_checkbox=True)
gb.configure_grid_options(domLayout='normal')

# Column Auto Fit
for col in df.columns:
    gb.configure_column(col, autoSize=True)

gridOptions = gb.build()

# =======================
#  SHOW GRID
# =======================
AgGrid(
    df,
    gridOptions=gridOptions,
    theme="material",
    update_mode=GridUpdateMode.NO_UPDATE,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    height=500
)
