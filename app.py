import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Billboard Dashboard", layout="wide")

# -----------------------------
# 1) READ EXCEL FILE
# -----------------------------

FILE_PATH = "Billboard.xlsm"

@st.cache_data
def load_data():
    df = pd.read_excel(FILE_PATH, sheet_name="Billboard Rentals")
    return df

df = load_data()

# -----------------------------
# 2) CLEAN DATE COLUMNS
# -----------------------------

date_cols = ["Booking Date", "Contract Start Date", "Contract End Date"]

for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors="coerce")

today = pd.to_datetime(datetime.today().date())

# -----------------------------
# 3) STATUS CALCULATION (SAFE)
# -----------------------------

def check_status(x):
    if pd.isna(x):
        return "Active"
    return "Expired" if x < today else "Active"

df["Status"] = df["Contract End Date"].apply(check_status)

# -----------------------------
# 4) SUMMARY DASHBOARD
# -----------------------------

total = len(df)
active = len(df[df["Status"] == "Active"])
expired = len(df[df["Status"] == "Expired"])

# Month Filter Summary
df_month = df[df["Booking Date"].dt.month == today.month]
rented_this_month = len(df_month)

# -----------------------------
# 5) UI STARTS
# -----------------------------

st.title("📊 Billboard Rental Dashboard")
st.write("Live Dashboard — Excel Connected Version")

# -----------------------------
# KPI ROW
# -----------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Billboards", total)
col2.metric("Active Contracts", active)
col3.metric("Expired Contracts", expired)
col4.metric("Rented This Month", rented_this_month)

st.divider()

# -----------------------------
# TABLE VIEW
# -----------------------------

st.subheader("📄 All Billboard Records")

search = st.text_input("Search Billboard, Client, Location…")

df_display = df.copy()

if search.strip() != "":
    df_display = df_display[
        df_display.apply(lambda row: search.lower() in row.astype(str).str.lower().to_string(), axis=1)
    ]

st.dataframe(df_display, use_container_width=True)

st.success("Dashboard Loaded Successfully ✔")
