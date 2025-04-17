import os
import json
from dotenv import load_dotenv
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# ✅ Vervang credentials.json door environment
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Retouren Overzicht").sheet1

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

        # Alleen verwerken als er iets retour komt
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
                reason
            ])

    return 'OK', 200

if __name__ == '__main__':
    app.run(port=5000)
