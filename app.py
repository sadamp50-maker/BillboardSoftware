import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Billboard Software", layout="wide")

st.title("📊 Billboard Management System")

# ----------------------------------------------------------
# 1) Load Excel File
# ----------------------------------------------------------

FILE_PATH = "Billboard.xlsm"   # Your file name in GitHub repo

@st.cache_data
def load_data():
    df = pd.read_excel(FILE_PATH, engine="openpyxl")

    # Columns that must convert to datetime
    date_cols = ["Contract Start Date", "Contract End Date"]

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Create Status Column
    today = pd.Timestamp.today()
    df["Contract Status (Active / Expired)"] = df["Contract End Date"].apply(
        lambda x: "Expired" if pd.isna(x) or x < today else "Active"
    )

    # Days remaining
    df["Days Remaining"] = df["Contract End Date"].apply(
        lambda x: (x - today).days if not pd.isna(x) else None
    )

    return df

df = load_data()

st.success("Excel File Loaded Successfully!")

# ----------------------------------------------------------
# 2) Filters
# ----------------------------------------------------------

st.sidebar.header("🔍 Filters")

status_filter = st.sidebar.selectbox(
    "Contract Status:",
    ["All", "Active", "Expired"]
)

client_filter = st.sidebar.text_input("Search Client Name:")

filtered_df = df.copy()

if status_filter != "All":
    filtered_df = filtered_df[
        filtered_df["Contract Status (Active / Expired)"] == status_filter
    ]

if client_filter:
    filtered_df = filtered_df[
        filtered_df["Client Name"].str.contains(client_filter, case=False, na=False)
    ]

# ----------------------------------------------------------
# 3) Show Table
# ----------------------------------------------------------

st.subheader("📋 Contract Records")

st.dataframe(filtered_df, use_container_width=True)

# ----------------------------------------------------------
# 4) Download Option
# ----------------------------------------------------------

st.download_button(
    "⬇ Download Filtered Excel",
    data=filtered_df.to_csv(index=False).encode("utf-8"),
    file_name="Filtered_Billboard_Data.csv",
    mime="text/csv"
)
