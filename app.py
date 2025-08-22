from flask import Flask, request, jsonify, render_template
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os, json

app = Flask(__name__)

# ----- CONFIG -----
SHEET_NAME = "Customer Data"
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# ----- HELPER: authorize gspread client -----
def get_gs_client():
    # Load credentials from Render environment variable (set GOOGLE_CREDS_JSON in Render dashboard)
    creds_info = json.loads(os.environ["GOOGLE_CREDS_JSON"])
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
    client = gspread.authorize(creds)
    return client

# Ensure sheet exists and has headers. Returns worksheet object.
def open_or_create_sheet():
    client = get_gs_client()
    try:
        sh = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = client.create(SHEET_NAME)

    worksheet = sh.sheet1

    # Ensure headers exist
    expected_headers = ["Customer Name", "Policy Number", "Email", "Date of Birth", "Phone", "Submitted At"]
    current_values = worksheet.row_values(1)
    if not current_values or len(current_values) < len(expected_headers):
        if current_values:
            worksheet.delete_rows(1)
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
        return jsonify([])

    if not value:
        return jsonify([])

    try:
        worksheet = open_or_create_sheet()
        records = worksheet.get_all_records()

        # case-insensitive exact match
        results = [r for r in records if str(r.get(sheet_field, "")).strip().lower() == value.lower()]

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
