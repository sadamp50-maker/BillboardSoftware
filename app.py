import streamlit as st
import pandas as pd

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Billboard Dashboard", layout="wide")

# ---- INITIAL DATAFRAME (50 rows) ----
columns = [
    "S No.", "Billboard ID", "Location / Address", "Billboard Size",
    "Client Name", "Company Name", "Contact Number", "Email",
    "Contract Start Date", "Contract End Date", "Rental Duration",
    "Rent Amount (PKR)", "Advance Received (PKR)", "Balance / Credit (PKR)",
    "Payment Status", "Contract Status", "Days Remaining",
    "Remarks / Notes", "Billboard Image / Link", "Partner’s Share"
]

df = pd.DataFrame({col: [""] * 50 for col in columns})
df["S No."] = range(1, 51)

st.title("📊 Billboard Management Dashboard")

st.write("Fill or edit the data below:")

# ---- Editable Table ----
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True
)

# ---- Export Section ----
st.subheader("📁 Export Data")

file_name = st.text_input("Enter file name:", "Billboard_Dashboard")

if st.button("Download Excel File"):
    excel_file = edited_df.to_excel(f"{file_name}.xlsx", index=False)
    st.success("File created! Check your working directory.")

# ---- Save to CSV ----
if st.button("Download CSV File"):
    edited_df.to_csv(f"{file_name}.csv", index=False)
    st.success("CSV file created!")
