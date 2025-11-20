import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Billboard Management", layout="wide")

FILE_PATH = "Billboard.xlsm"


# ----------------------------------------------------------
# Load & Save Functions
# ----------------------------------------------------------

@st.cache_data
def load_data():
    df = pd.read_excel(FILE_PATH, engine="openpyxl")

    # Fix date columns
    date_cols = ["Contract Start Date", "Contract End Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    today = pd.Timestamp.today()

    # Status
    df["Status"] = df["Contract End Date"].apply(
        lambda x: "Expired" if pd.isna(x) or x < today else "Active"
    )

    # Days Remaining
    df["Days Remaining"] = df["Contract End Date"].apply(
        lambda x: (x - today).days if not pd.isna(x) else None
    )

    return df


def save_data(df):
    df.to_excel(FILE_PATH, index=False, engine="openpyxl")


df = load_data()


# ----------------------------------------------------------
# Sidebar Menu
# ----------------------------------------------------------

st.sidebar.title("📌 Menu")
menu = st.sidebar.radio(
    "Choose an option:",
    ["Dashboard", "View Records", "Add New Record", "Edit/Delete Record"]
)


# ----------------------------------------------------------
# 🟦 Dashboard
# ----------------------------------------------------------

if menu == "Dashboard":
    st.title("📊 Billboard Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Boards", len(df))

    with col2:
        st.metric("Active Contracts", len(df[df["Status"] == "Active"]))

    with col3:
        st.metric("Expired Contracts", len(df[df["Status"] == "Expired"]))

    st.subheader("Status Chart")
    st.bar_chart(df["Status"].value_counts())

    st.subheader("Days Remaining (Histogram)")
    st.bar_chart(df["Days Remaining"])


# ----------------------------------------------------------
# 🟦 View Records
# ----------------------------------------------------------

elif menu == "View Records":
    st.title("📋 All Records")

    search_name = st.text_input("Search by Client Name")

    filtered = df.copy()
    if search_name:
        filtered = filtered[
            filtered["Client Name"].str.contains(search_name, case=False, na=False)
        ]

    st.dataframe(filtered, use_container_width=True)


# ----------------------------------------------------------
# 🟦 Add New Record
# ----------------------------------------------------------

elif menu == "Add New Record":
    st.title("➕ Add New Billboard Contract")

    col1, col2 = st.columns(2)

    with col1:
        client = st.text_input("Client Name")
        location = st.text_input("Location")
        size = st.text_input("Board Size")

    with col2:
        start_date = st.date_input("Contract Start Date")
        end_date = st.date_input("Contract End Date")

    if st.button("Add Record"):
        new_row = {
            "Client Name": client,
            "Location": location,
            "Board Size": size,
            "Contract Start Date": pd.to_datetime(start_date),
            "Contract End Date": pd.to_datetime(end_date),
        }

        df = df.append(new_row, ignore_index=True)
        save_data(df)
        st.success("Record Added Successfully!")


# ----------------------------------------------------------
# 🟦 Edit/Delete Record
# ----------------------------------------------------------

elif menu == "Edit/Delete Record":
    st.title("✏ Edit or Delete Record")

    selected_client = st.selectbox(
        "Select Client to Edit",
        df["Client Name"].unique()
    )

    record = df[df["Client Name"] == selected_client].iloc[0]

    client = st.text_input("Client Name", record["Client Name"])
    location = st.text_input("Location", record["Location"])
    size = st.text_input("Board Size", record["Board Size"])

    start_date = st.date_input(
        "Contract Start Date", record["Contract Start Date"].date()
    )
    end_date = st.date_input(
        "Contract End Date", record["Contract End Date"].date()
    )

    if st.button("Update"):
        df.loc[df["Client Name"] == selected_client, "Client Name"] = client
        df.loc[df["Client Name"] == selected_client, "Location"] = location
        df.loc[df["Client Name"] == selected_client, "Board Size"] = size
        df.loc[df["Client Name"] == selected_client, "Contract Start Date"] = pd.to_datetime(start_date)
        df.loc[df["Client Name"] == selected_client, "Contract End Date"] = pd.to_datetime(end_date)

        save_data(df)
        st.success("Record Updated Successfully!")

    if st.button("Delete"):
        df = df[df["Client Name"] != selected_client]
        save_data(df)
        st.error("Record Deleted Successfully!")
