import streamlit as st
import pandas as pd
import datetime as dt
from openpyxl import load_workbook

st.set_page_config(page_title="Billboard Dashboard", layout="wide")

# ------------------------------
# Load Excel File
# ------------------------------
excel_file = "Billboard.xlsm"
sheet_name = "Billboard Rentals"

df = pd.read_excel(excel_file, sheet_name=sheet_name)

# ------------------------------
# Calculate STATUS
# ------------------------------
today = dt.date.today()

df["Contract Start Date"] = pd.to_datetime(df["Contract Start Date"]).dt.date
df["Contract End Date"] = pd.to_datetime(df["Contract End Date"]).dt.date

df["Status"] = df["Contract End Date"].apply(
    lambda x: "Expired" if x < today else "Active"
)

# ------------------------------
# Dashboard KPIs
# ------------------------------
total_sites = len(df)
active_sites = len(df[df["Status"] == "Active"])
expired_sites = len(df[df["Status"] == "Expired"])

total_rent = df["Rent Amount"].sum()
active_rent = df[df["Status"] == "Active"]["Rent Amount"].sum()
expired_rent = df[df["Status"] == "Expired"]["Rent Amount"].sum()

# ------------------------------
# Layout: KPI Cards
# ------------------------------
st.title("📊 Billboard Management Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Billboards", total_sites)
col2.metric("Active Contracts", active_sites)
col3.metric("Expired Contracts", expired_sites)
col4.metric("Total Rent Amount", f"Rs {total_rent:,.0f}")

st.markdown("---")

# ------------------------------
# Charts
# ------------------------------
st.subheader("📈 Active vs Expired Billboards")

status_count = df["Status"].value_counts()

st.bar_chart(status_count)

st.markdown("---")

# Monthly Rent Summary
st.subheader("💰 Rent Summary")

rent_data = pd.DataFrame({
    "Status": ["Active", "Expired"],
    "Rent Amount": [active_rent, expired_rent]
})

st.bar_chart(rent_data.set_index("Status"))

st.markdown("---")

# ------------------------------
# Detailed Table
# ------------------------------
st.subheader("📋 Complete Billboard Data")

with st.expander("Show Full Table"):
    st.dataframe(df, height=500)
