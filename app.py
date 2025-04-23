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

# Configuratie via omgevingsvariabelen
QLS_USERNAME = os.environ.get("QLS_USERNAME")
QLS_PASSWORD = os.environ.get("QLS_PASSWORD")
QLS_COMPANY_ID = os.environ.get("QLS_COMPANY_ID")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE_URL")  # b.v. 'mijnwinkel.myshopify.com'
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")

app = Flask(__name__)

# Google Sheets setup
gscope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, gscope)
client = gspread.authorize(creds)
sheet = client.open("Retouren Overzicht").sheet1

# Shopify fallback: zoek productnaam op basis van SKU via Admin API
def get_product_name_from_shopify(sku: str) -> str:
    if not sku:
        return ""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-04/products.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_TOKEN
    }
    params = {"limit": 250, "fields": "id,title,variants"}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"❌ Shopify API error: {resp.status_code}")
        return ""
    for product in resp.json().get("products", []):
        for v in product.get("variants", []):
            if v.get("sku") == sku:
                return product.get("title", "")
    print(f"⚠️ Geen Shopify product gevonden voor SKU={sku}")
    return ""

# QLS primary: zoek productnaam op via fulfillment_products list endpoint
def get_product_name_from_qls(sku: str) -> str:
    if not sku:
        return ""
    url = f"https://api.pakketdienstqls.nl/companies/{QLS_COMPANY_ID}/fulfillment_products"
    # filter=equals(sku,"...") per Swagger
    params = {"filter": f"equals(sku,\"{sku}\")"}
    resp = requests.get(url, auth=HTTPBasicAuth(QLS_USERNAME, QLS_PASSWORD), params=params)
    if resp.status_code != 200:
        print(f"❌ QLS API error for SKU={sku}: {resp.status_code}")
        return ""
    try:
        products = resp.json()
    except ValueError:
        print(f"❌ Ongeldige JSON van QLS voor SKU={sku}")
        return ""
    if isinstance(products, list) and products:
        return products[0].get("name", "")
    print(f"⚠️ Geen QLS product gevonden voor SKU={sku}")
    return ""

@app.route('/webhook/retouren', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    print("Webhook ontvangen:", json.dumps(data, indent=2))
    items = data.get('return_products', [])
    for item in items:
        sku = item.get('fulfillment_product', {}).get('sku', '')
        qty = item.get('amount_expected', 0)
        reason = item.get('reason', '')
        if qty and int(qty) > 0:
            # Probeer eerst QLS, fallback naar Shopify
            name = get_product_name_from_qls(sku) or get_product_name_from_shopify(sku)
            row = [
                datetime.utcnow().isoformat(),
                data.get('id', ''),
                data.get('status', ''),
                data.get('consumer_contact', {}).get('name', ''),
                data.get('return_shipment', {}).get('tracking_number', ''),
                data.get('brand', {}).get('name', ''),
                sku,
                qty,
                reason,
                name
            ]
            sheet.append_row(row)
            print(f"✅ Toegevoegd: SKU={sku}, Name={name}")
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
