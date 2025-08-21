from flask import Flask, request, jsonify, render_template, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

from flask import jsonify

app = Flask(__name__)

# ----- CONFIG -----
# Name of your Google Sheet (exact title)
SHEET_NAME = "Customer Data"

# Path to service account JSON (ensure file is in project root and kept secret)
SERVICE_ACCOUNT_FILE = "service_account.json"

# Scopes required for Google Sheets + Drive
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# ----- HELPER: authorize gspread client -----
def get_gs_client():
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPE)
    client = gspread.authorize(creds)
    return client

# Ensure sheet exists and has headers. Returns worksheet object.
def open_or_create_sheet():
    client = get_gs_client()

    try:
        sh = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        # Create a new spreadsheet if missing (in the service account's Drive).
        sh = client.create(SHEET_NAME)
        # Note: you still need to share spreadsheet with others if you want them to view/edit.

    worksheet = sh.sheet1

    # Ensure headers exist (first row). Change/add headers as needed.
    expected_headers = ["Customer Name", "Policy Number", "Email", "Date of Birth", "Phone", "Submitted At"]
    current_values = worksheet.row_values(1)
    if not current_values or len(current_values) < len(expected_headers):
        # If first row empty or headers missing, set headers
        worksheet.delete_rows(1) if current_values else None
        worksheet.insert_row(expected_headers, index=1)
    return worksheet

# ----- ROUTES -----
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/entry")
def entry():
    return render_template("entry.html")

@app.route("/search")
def search():
    return render_template("search.html")

# Receive JSON from frontend and append to sheet
@app.route("/add_customer", methods=["POST"])
def add_customer():
    try:
        data = request.get_json(force=True)
        # basic required fields
        customername = data.get("customername", "").strip()
        policyNumber = data.get("policyNumber", "").strip()
        email = data.get("email", "").strip()
        dateOfBirth = data.get("dateOfBirth", "").strip()
        phone = data.get("phone", "").strip()

        if not customername or not policyNumber or not phone:
            return jsonify({"status": "error", "message": "Missing required fields (name, policyNumber, phone)."}), 400

        worksheet = open_or_create_sheet()

        submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S (UTC)")

        row = [customername, policyNumber, email, dateOfBirth, phone, submitted_at]
        worksheet.append_row(row, value_input_option="USER_ENTERED")

        return jsonify({"status": "success", "message": "Data added to Google Sheets!"})
    except Exception as e:
        # For debugging you may want to log e to a file, but don't return private details in production.
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/search_customer", methods=["POST"])
def search_customer():
    data = request.get_json()
    search_by = data.get("searchBy")
    value = ""
    
    if search_by == "name":
        value = data.get("customername", "").strip()
        sheet_field = "Customer Name"
    elif search_by == "policy":
        value = data.get("policyNumber", "").strip()
        sheet_field = "Policy Number"
    else:
        return jsonify([])  # return empty list for invalid search

    if not value:
        return jsonify([])

    try:
        worksheet = open_or_create_sheet()
        records = worksheet.get_all_records()

        # case-insensitive exact match
        results = [r for r in records if str(r.get(sheet_field, "")).strip().lower() == value.lower()]

        # OR partial match (uncomment for contains)
        # results = [r for r in records if value.lower() in str(r.get(sheet_field, "")).lower()]

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    # Ensure service account file exists
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: {SERVICE_ACCOUNT_FILE} not found. Place your service account JSON in the project root.")
    app.run(debug=True)
