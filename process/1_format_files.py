import pandas as pd
from util import format_string

def process_ca_green_area(file_path="data/raw/ca_area.xlsx"):
    # Import Cankaya Green Area Sheet
    ca_green_area_df = pd.read_excel(file_path, sheet_name=0, header=4)
    # Remove "SIRA NO" rows with non-numeric or na values
    ca_green_area_df = ca_green_area_df[
        pd.to_numeric(ca_green_area_df["SIRA NO"], errors="coerce").notna()
    ]
    # Convert "SIRA NO" to integer type
    ca_green_area_df["SIRA NO"] = ca_green_area_df["SIRA NO"].astype(int)
    return ca_green_area_df

def process_all_invoice_to_ca_invoice(file_path="data/raw/all_invoice.csv"):
    # Import all invoices
    invoice_df = pd.read_csv(file_path)
    # Get only CANKAYA invoices
    ca_invoice_df = invoice_df[invoice_df.district == "ÇANKAYA"].copy()

    # Remove "ÇANKAYA BELEDİYESİ" from the "name" column and strip whitespace
    ca_invoice_df["name"] = (
        ca_invoice_df["name"].str.replace("ÇANKAYA BELEDİYESİ", "", regex=False).str.strip()
    )
    
    # Strip whitespace from column names
    ca_invoice_df.columns = ca_invoice_df.columns.str.strip()

    # Convert date columns to datetime.date
    ca_invoice_df["start_read_date"] = pd.to_datetime(ca_invoice_df["start_read_date"]).dt.date
    ca_invoice_df["end_read_date"] = pd.to_datetime(ca_invoice_df["end_read_date"]).dt.date
    return ca_invoice_df

def process_irrigation(file_path="data/raw/ca_irrigation.csv"):
    irrigation_df = pd.read_csv(file_path)
    irrigation_df["name"] = irrigation_df["name"].apply(format_string.turkish_upper)
    return irrigation_df

def main():
    # Process and save area
    process_ca_green_area().to_csv("data/processed/ca_area.csv", index=False)

    # Process and save all_invoices to ca_invoice
    process_all_invoice_to_ca_invoice().to_csv("data/processed/ca_invoice.csv", index=False)

    # Process and save irrigation
    process_irrigation().to_csv("data/processed/ca_irrigation.csv", index=False)

if __name__ == "__main__":
    main()

