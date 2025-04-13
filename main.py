import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt

# File to store transactions
data_file = "finance_data.csv"

# Initialize data file
if not os.path.exists(data_file):
    pd.DataFrame(columns=["Date", "Type", "Category", "Description", "Amount"]).to_csv(data_file, index=False)

# Load data
def load_data():
    try:
        df = pd.read_csv(data_file, parse_dates=["Date"])
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        return df.dropna()
    except:
        return pd.DataFrame(columns=["Date", "Type", "Category", "Description", "Amount"])

# Save new transaction
def save_transaction(date, t_type, category, description, amount):
    new_entry = pd.DataFrame([[date, t_type, category, description, amount]],
                             columns=["Date", "Type", "Category", "Description", "Amount"])
    new_entry.to_csv(data_file, mode='a', header=False, index=False)

# Generate summary plots
def plot_summary(df, return_figs=False, key_suffix=""):
    st.subheader("📈 Income vs Expense Trend")
    if df.empty:
        st.warning("No data available to show.")
        return [], []

    trend = df.groupby(["Date", "Type"])["Amount"].sum().reset_index()
    fig1 = px.line(trend, x="Date", y="Amount", color="Type", markers=True, title="Daily Income vs Expense")
    st.plotly_chart(fig1, use_container_width=True, key=f"line_chart_{key_suffix}")

    st.subheader("📊 Category-wise Distribution")
    fig2 = None
    if "Category" in df.columns and not df["Category"].isnull().all():
        cat_df = df.groupby("Category")["Amount"].sum().reset_index()
        fig2 = px.pie(cat_df, values="Amount", names="Category", title="Spending by Category")
        st.plotly_chart(fig2, use_container_width=True, key=f"pie_chart_{key_suffix}")

    return fig1, fig2

# Download buttons
def get_csv_download(data):
    return data.to_csv(index=False).encode('utf-8')

def get_excel_download(data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

def save_plot_as_image(fig, filename):
    fig.write_image(filename)
    return filename

def get_pdf_download(data):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Finance Report", styles['Title']), Spacer(1, 12)]

    for i, row in data.iterrows():
        line = f"{row['Date']} | {row['Type']} | {row['Category']} | {row['Description']} | {row['Amount']}"
        elements.append(Paragraph(line, styles['Normal']))
        elements.append(Spacer(1, 6))

    # Save plots as image
    fig1, fig2 = plot_summary(data, return_figs=True, key_suffix="pdf")
    img_path1, img_path2 = None, None
    if fig1:
        img_path1 = "trend_plot.png"
        fig1.write_image(img_path1)
        elements.append(Spacer(1, 12))
        elements.append(Image(img_path1, width=480, height=250))

    if fig2:
        img_path2 = "pie_chart.png"
        fig2.write_image(img_path2)
        elements.append(Spacer(1, 12))
        elements.append(Image(img_path2, width=400, height=250))

    doc.build(elements)
    output.seek(0)

    if img_path1 and os.path.exists(img_path1):
        os.remove(img_path1)
    if img_path2 and os.path.exists(img_path2):
        os.remove(img_path2)

    return output.getvalue()

# Analyze uploaded file
def analyze_uploaded_file(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.lower()

        if not {'date', 'amount'}.issubset(df.columns):
            st.error("Uploaded CSV must contain 'Date' and 'Amount' columns.")
            return

        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df["amount"] = pd.to_numeric(df["amount"], errors='coerce')
        df.dropna(subset=["date", "amount"], inplace=True)

        df.rename(columns={"date": "Date", "amount": "Amount"}, inplace=True)

        df["Type"] = df["Amount"].apply(lambda x: "Income" if x >= 0 else "Expense")

        if "category" not in df.columns:
            df["Category"] = "Uncategorized"
        else:
            df.rename(columns={"category": "Category"}, inplace=True)

        if "description" not in df.columns:
            df["Description"] = ""

        st.success("✅ File uploaded and processed successfully!")
        st.dataframe(df, use_container_width=True)

        plot_summary(df, key_suffix="upload")

        st.subheader("⬇️ Download Processed Data")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("Download CSV", get_csv_download(df), file_name="uploaded_finance_data.csv", mime="text/csv")
        with col2:
            st.download_button("Download Excel", get_excel_download(df), file_name="uploaded_finance_data.xlsx", mime="application/vnd.ms-excel")
        with col3:
            st.download_button("Download PDF", get_pdf_download(df), file_name="uploaded_finance_data.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

# App UI
st.set_page_config(page_title="📈Trend Analysis & Finance Tracker", layout="centered")
st.title("Trend Analysis & Finance Tracker")

menu = st.sidebar.radio("Navigation", ["Add Transaction", "View Summary", "Trend Analysis"])

if menu == "Add Transaction":
    st.header("➕ Add Transaction")
    with st.form("add_form"):
        date = st.date_input("Date", value=datetime.date.today())
        t_type = st.selectbox("Type", ["Income", "Expense"])
        category = st.text_input("Category")
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.01)
        submit = st.form_submit_button("Add")

    if submit:
        save_transaction(date, t_type, category, description, amount)
        st.success("Transaction saved successfully!")

elif menu == "View Summary":
    st.header("📊 Summary")
    data = load_data()
    st.dataframe(data, use_container_width=True)
    plot_summary(data, key_suffix="summary")

    if not data.empty:
        st.subheader("⬇️ Download Data")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("Download CSV", get_csv_download(data), file_name="finance_data.csv", mime="text/csv")
        with col2:
            st.download_button("Download Excel", get_excel_download(data), file_name="finance_data.xlsx", mime="application/vnd.ms-excel")
        with col3:
            st.download_button("Download PDF", get_pdf_download(data), file_name="finance_data.pdf", mime="application/pdf")

elif menu == "Trend Analysis":
    st.header("📂 Trend Analysis")
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])
    if uploaded_file:
        analyze_uploaded_file(uploaded_file)

# Footer
st.markdown("""
---
<p style='text-align: center;'>
    Made with ❤️ by <b>Im_Dev</b> &nbsp;|&nbsp;
    <a href="https://github.com/Dev-comett" target="_blank">🐱 GitHub</a> &nbsp;|&nbsp;
    <a href="https://www.linkedin.com/in/dev-ice/" target="_blank">💼 LinkedIn</a>
</p>
""", unsafe_allow_html=True)
