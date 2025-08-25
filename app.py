from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os

app = Flask(__name__)

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("service_account.json")  # make sure this file is in your project root
    firebase_admin.initialize_app(cred)

db = firestore.client()
customers_ref = db.collection("customers")

# Home
@app.route("/")
def home():
    return render_template("index.html")

# Entry Page
@app.route("/entry")
def entry():
    return render_template("entry.html")

# Save customer data
@app.route("/add_customer", methods=["POST"])
def save_customer():
    try:
        data = request.json

        # Store with clean keys (no spaces)
        customer_data = {
            "customername": data.get("customername"),
            "policyNumber": data.get("policyNumber"),
            "email": data.get("email"),
            "dateOfBirth": data.get("dateOfBirth"),
            "phone": data.get("phone"),
        }

        customers_ref.add(customer_data)

        return jsonify({"status": "success", "message": "Customer saved successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Search Page
@app.route("/search")
def search():
    return render_template("search.html")

# Search API
@app.route("/search_customer", methods=["POST"])
def search_customer():
    try:
        data = request.json
        search_by = data.get("searchBy")
        value = None

        if search_by == "name":
            value = data.get("customername")
            query = customers_ref.where("customername", "==", value).stream()
        elif search_by == "policy":
            value = data.get("policyNumber")
            query = customers_ref.where("policyNumber", "==", value).stream()
        else:
            return jsonify([])

        results = [doc.to_dict() for doc in query]

        return jsonify(results)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
