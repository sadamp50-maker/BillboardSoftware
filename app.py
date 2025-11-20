import streamlit as st
import pandas as pd

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Billboard Dashboard", layout="wide")

# ---- COLUMNS ----
columns = [
    "S No.", "Billboard ID", "Location / Address", "Billboard Size",
    "Client Name", "Company Name", "Contact Number", "Email",
    "Contract Start Date", "Contract End Date", "Rental Duration",
    "Rent Amount (PKR)", "Advance Received (PKR)", "Balance / Credit (PKR)",
    "Payment Status", "Contract Status", "Days Remaining",
    "Remarks / Notes", "Billboard Image / Link", "Partner’s Share"
]

# ---- INITIAL 50 ROW DATA ----
df = pd.DataFrame({col: [""] * 50 for col in columns})
df["S No."] = range(1, 51)

st.title("📊 Billboard Management Dashboard")

st.write("Fill or edit the data below:")

# ---- Editable table ----
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    key="editor"
)

# ---- DARKER COLORS STYLE ----
def style_table(x):
    df_styled = pd.DataFrame('', index=x.index, columns=x.columns)
    for i in range(len(x)):
        if i % 2 == 0:
            df_styled.iloc[i] = 'background-color: #d2e2ff;'   # darker light blue
        else:
            df_styled.iloc[i] = 'background-color: #e6dfff;'   # darker light lavender
    return df_styled

styled = edited_df.style.apply(style_table, axis=None)\
    .set_table_styles([
        {
            'selector': 'th',
            'props': [
                ('background-color', '#9bbcff'),
                ('color', 'black'),
                ('font-weight', 'bold')
            ]
        }
    ])

st.subheader("📘 Styled Table View (Dark Colors Applied)")
st.dataframe(styled, use_container_width=True)

# ---- EXPORT OPTIONS ----
st.subheader("📁 Export Data")

file_name = st.text_input("Enter file name:", "Billboard_Dashboard")

if st.button("Download Excel File"):
    edited_df.to_excel(f"{file_name}.xlsx", index=False)
    st.success("Excel file created successfully!")

if st.button("Download CSV File"):
    edited_df.to_csv(f"{file_name}.csv", index=False)
    st.success("CSV file created successfully!")
