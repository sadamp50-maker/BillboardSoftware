import streamlit as st
import pandas as pd

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

# Create initial empty data
df = pd.DataFrame({col: [""] * 50 for col in columns})
df["S No."] = range(1, 51)

st.title("📊 Billboard Management Dashboard (Advanced Table)")

# Convert df to HTML with custom JS for editing
table_html = df.to_html(
    index=False,
    classes="styled-table",
    escape=False
)

# Inject CSS + JS
page = f"""
<style>
/* Table Layout */
.styled-table {{
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 15px;
    width: 100%;
    border: 1px solid #ccc;
}}

.styled-table th {{
    background-color: #b7ccff; 
    color: black;
    text-align: left;
    padding: 10px;
}}

.styled-table td {{
    padding: 8px;
    border: 1px solid #ddd;
}}

/* Row Colors (Medium Colors) */
.styled-table tr:nth-child(even) {{
    background-color: #e0e8ff;
}}

.styled-table tr:nth-child(odd) {{
    background-color: #f0e8ff;
}}

/* Editable cell highlight */
td:focus {{
    outline: 2px solid #6a8cff;
    background-color: #dbe4ff;
}}
</style>

<script>
// Make all table cells editable except headers
document.addEventListener("DOMContentLoaded", function() {{
    let cells = document.querySelectorAll("td");
    cells.forEach(cell => {{
        cell.contentEditable = "true";
    }});
}});
</script>

{table_html}
"""

st.markdown(page, unsafe_allow_html=True)
