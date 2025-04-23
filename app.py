import os
import json
from dotenv import load_dotenv
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

# Laad omgevingsvariabelen
load_dotenv()

# QLS Auth gegevens
QLS_USERNAME = os.environ.get("QLS_USERNAME")
QLS_PASSWORD = os.environ.get("QLS_PASSWORD")
QLS_COMPANY_ID = os.environ.get("QLS_COMPANY_ID")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON")

app = Flask(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Retouren Overzicht").sheet1

# Functie om productnaam op te halen via QLS list endpoint met SKU filter

def get_product_name_from_qls(sku: str) -> str:
    """
    Haal de productnaam op uit QLS API door te filteren op SKU via list endpoint.
    Probeer via filter[sku] query parameter.
    """
    if not sku:
        return ""
    url = f"https://api.pakketdienstqls.nl/companies/{QLS_COMPANY_ID}/fulfillment_products"
    # Gebruik filter[sku] param
    params = {"filter[sku]": sku}
    response = requests.get(
        url,
        auth=HTTPBasicAuth(QLS_USERNAME, QLS_PASSWORD),
        params=params
    )
    if response.status_code == 200:
        payload = response.json()
        items = payload.get("data", [])
        if items:
            # JSON-API: naam onder data[].attributes.name
            return items[0].get("attributes", {}).get("name", "")
        else:
            print(f"⚠️ Geen producten gevonden voor SKU={sku}")
            return ""
    else:
        print(f"❌ Fout bij ophalen productenlijst voor SKU={sku}, status={response.status_code}")
        return ""

@app.route('/webhook/retouren', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    print("Webhook ontvangen:", json.dumps(data, indent=2))

    items = data.get('return_products', [])
    for item in items:
        sku = item.get('fulfillment_product', {}).get('sku', '')
        quantity = item.get('amount_expected', 0)
        reason = item.get('reason', '')

        if quantity and int(quantity) > 0:
            # Haal productnaam op via SKU
            product_name = get_product_name_from_qls(sku)
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
