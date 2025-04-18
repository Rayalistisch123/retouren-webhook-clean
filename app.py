import os
import json
from dotenv import load_dotenv
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

load_dotenv()

app = Flask(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Retouren Overzicht").sheet1

# QLS Auth gegevens
QLS_USERNAME = os.environ.get("QLS_USERNAME")
QLS_PASSWORD = os.environ.get("QLS_PASSWORD")
QLS_COMPANY_ID = os.environ.get("QLS_COMPANY_ID")

# Functie om productnaam op te halen uit QLS API

def get_product_name_from_qls(product_id):
    url = f"https://api.pakketdienstqls.nl/companies/{QLS_COMPANY_ID}/fulfillment_products/{product_id}"
    response = requests.get(url, auth=HTTPBasicAuth(QLS_USERNAME, QLS_PASSWORD))

    if response.status_code == 200:
        data = response.json()
        return data.get("name", "")
    else:
        print(f"❌ Fout bij ophalen productnaam voor ID {product_id}. Status: {response.status_code}")
        return ""

@app.route('/webhook/retouren', methods=['POST'])
def webhook():
    data = request.json
    print("Webhook ontvangen:")
    print(data)

    items = data.get('return_products', [])
    print(f"Items gevonden: {items}")

    for item in items:
        sku = item.get('fulfillment_product', {}).get('sku', '')
        quantity = item.get('amount_expected', 0)
        reason = item.get('reason', '')
        product_id = item.get('fulfillment_product', {}).get('id', '')
        product_name = get_product_name_from_qls(product_id)

        if quantity and int(quantity) > 0:
            timestamp = datetime.utcnow().isoformat()
            return_id = data.get('id', '')
            status = data.get('status', '')
            customer = data.get('consumer_contact', {}).get('name', '')
            tracking = data.get('return_shipment', {}).get('tracking_number', '')
            brand = data.get('brand', {}).get('name', '')

            sheet.append_row([
                timestamp,
                return_id,
                status,
                customer,
                tracking,
                brand,
                sku,
                quantity,
                reason,
                product_name
            ])

    return 'OK', 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)