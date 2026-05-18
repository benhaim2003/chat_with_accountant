"""
Generates realistic mock PDF documents in dummy_files/ for each client.
Run once: python scripts/generate_mock_pdfs.py
Requires: fpdf2 (pip install fpdf2)
"""
from __future__ import annotations
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos


def _pdf(title: str, lines: list[str]) -> FPDF:
    doc = FPDF()
    doc.add_page()
    doc.set_font("Helvetica", style="B", size=16)
    doc.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    doc.ln(4)
    doc.set_font("Helvetica", size=11)
    for line in lines:
        doc.cell(0, 7, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return doc


def electricity_bill(client_name: str, month: str) -> FPDF:
    return _pdf("ELECTRICITY BILL", [
        "Israel Electric Corporation",
        f"Customer: {client_name}",
        f"Billing Period: {month}",
        "Previous Meter Reading: 7,940 kWh",
        "Current Meter Reading:  8,420 kWh",
        "Consumption: 480 kWh",
        "Energy Charge (ILS 0.60/kWh): ILS 288.00",
        "Distribution Fee: ILS 42.00",
        "VAT (17%): ILS 56.10",
        "Total Amount Due: ILS 386.10",
        f"Due Date: {month}-28",
    ])


def water_bill(client_name: str, month: str) -> FPDF:
    return _pdf("WATER BILL", [
        "Municipal Water Authority",
        f"Customer: {client_name}",
        f"Billing Period: {month}",
        "Water Consumption: 125 cubic meters",
        "Sewage: 100 cubic meters",
        "Water Charge: ILS 280.00",
        "Sewage Charge: ILS 180.00",
        "VAT (17%): ILS 77.60",
        "Total Amount Due: ILS 537.60",
        f"Due Date: {month}-25",
    ])


def tax_invoice(client_name: str, month: str) -> FPDF:
    return _pdf("TAX INVOICE", [
        "Invoice Number: INV-2026-0512",
        f"Invoice Date: {month}-15",
        "Supplier: ABC Supplies Ltd.",
        "Supplier VAT Registration: 514123456",
        f"Customer: {client_name}",
        "Description: Office Supplies & Equipment",
        "Quantity: 10 units  x  ILS 50.00",
        "Subtotal: ILS 500.00",
        "VAT (17%): ILS 85.00",
        "Total Amount: ILS 585.00",
        "Payment Terms: Net 30",
    ])


def salary_slip(client_name: str, month: str) -> FPDF:
    return _pdf("SALARY SLIP / PAY STUB", [
        f"Employer: {client_name}",
        "Employee Name: David Cohen",
        "Employee ID: EMP-0042",
        f"Pay Period: {month}",
        "Basic Salary:         ILS 8,000.00",
        "Overtime Pay:         ILS   500.00",
        "Gross Salary:         ILS 8,500.00",
        "--- Deductions ---",
        "Income Tax:           ILS 1,200.00",
        "National Insurance:   ILS   350.00",
        "Health Insurance:     ILS   120.00",
        "Total Deductions:     ILS 1,670.00",
        "Net Salary Paid:      ILS 6,830.00",
        "Bank Transfer: Bank Hapoalim  IL62-0108-0000-0009-9999-123",
    ])


def bank_statement(client_name: str, month: str) -> FPDF:
    return _pdf("BANK STATEMENT", [
        "Bank Hapoalim Ltd.",
        f"Account Holder: {client_name}",
        "Account Number: 123-456789-0",
        f"Statement Period: 01 {month} - 30 {month}",
        "Opening Balance: ILS 45,230.00",
        "--- Credits ---",
        f"  {month}-03  Customer Payment     ILS 12,000.00",
        f"  {month}-10  Wire Transfer        ILS  8,500.00",
        "Total Credits:   ILS 20,500.00",
        "--- Debits ---",
        f"  {month}-05  Supplier Payment     ILS  4,200.00",
        f"  {month}-15  Office Rent          ILS  6,000.00",
        "Total Debits:    ILS 10,200.00",
        "Closing Balance: ILS 55,530.00",
    ])


GENERATORS = {
    "electricity_bill": electricity_bill,
    "water_bill":       water_bill,
    "tax_invoice":      tax_invoice,
    "salary_slip":      salary_slip,
    "bank_statement":   bank_statement,
}

CLIENTS: dict[str, dict] = {
    "C001_Levi_Enterprises": {
        "name": "Levi Enterprises",
        "docs": ["electricity_bill", "water_bill", "tax_invoice", "salary_slip", "bank_statement"],
    },
    "C002_Goldberg_Tech": {
        "name": "Goldberg Tech",
        "docs": ["electricity_bill", "water_bill", "salary_slip"],
    },
    "C003_Ben_David_Restaurant": {
        "name": "Ben-David Restaurant",
        "docs": ["water_bill", "tax_invoice", "bank_statement"],
    },
    "C004_Shapiro_Services": {
        "name": "Shapiro Services",
        "docs": ["bank_statement"],
    },
}

MONTH = "2026-05"
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "dummy_files")


def main() -> None:
    for folder, info in CLIENTS.items():
        out_dir = os.path.join(BASE_DIR, folder)
        os.makedirs(out_dir, exist_ok=True)
        for doc_type in info["docs"]:
            filename = f"{doc_type}_{MONTH.replace('-', '_')}.pdf"
            path = os.path.join(out_dir, filename)
            pdf = GENERATORS[doc_type](info["name"], MONTH)
            pdf.output(path)
            print(f"  created  {os.path.relpath(path)}")
    print(f"\nDone — {sum(len(v['docs']) for v in CLIENTS.values())} PDFs generated.")


if __name__ == "__main__":
    main()
