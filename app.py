from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)

# Verbinding met Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Retouren Overzicht").sheet1  # pas aan naar jouw sheetnaam

@app.route('/webhook/retouren', methods=['POST'])
def webhook():
    data = request.json
    print("Webhook ontvangen:")
    print(data)

    items = data.get('return_products', [])
    print(f"Items gevonden: {items}")

    for item in items:
        sku = item.get('fulfillment_product', {}).get('sku', '')
        quantity = item.get('amount_expected', '')
        reason = item.get('reason', '')

    if quantity > 0:
        timestamp = datetime.utcnow().isoformat()
        return_id = data.get('id', '')
        status = data.get('status', '')
        customer = data.get('consumer_contact', {}).get('name', '')
        tracking = data.get('return_shipment', {}).get('tracking_number', '')  # momenteel vaak leeg
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
