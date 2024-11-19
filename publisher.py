import pulsar
import requests
import json
import time
from datetime import datetime
from flask import Flask, request, render_template, jsonify
import threading
app = Flask(__name__)

# Set up Pulsar client
client = pulsar.Client('pulsar://localhost:6650')

# Polygon API key
API_KEY = 'ovAiIDjIIhxampLoLnI6a0GEA1u6rYtM'

#url stocks real time preview
BASE_URL = 'https://api.polygon.io/v2/aggs/ticker/{}/prev'

#function to fetch data about stock of a company
def fetch_stock_data(stock_symbol):
    """Fetch stock data from Polygon API based on the selected stock symbol."""
    url = BASE_URL.format(stock_symbol) + f'?apiKey={API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['results'][0]  # Return the first result
    else:
        return None

#fromatting message for pulsar topics
def format_message(stock_symbol, stock_data):
    # Format stock data to JSON for Pulsar
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = {
        # company stock name
        'symbol': stock_symbol,
        # Close price
        'price': stock_data['c'],  
        #timestamp
        'timestamp': timestamp
    }
    return json.dumps(message)

#function to create a producer for a certain topic
def get_producer_for_symbol(stock_symbol):
    """Get or create a Pulsar producer for a specific stock symbol topic."""
    topic_name = f'stock-{stock_symbol}'  # Topic name based on stock symbol
    return client.create_producer(topic_name)


#function to publish stock data in the topic
def publish_stock_data(stock_symbol):
    """Fetch stock data and publish it to Pulsar."""
    producer = get_producer_for_symbol(stock_symbol)

    while True:
        # Get stock data
        stock_data = fetch_stock_data(stock_symbol)
        # data elaboration
        if stock_data:
            #message formatting
            message = format_message(stock_symbol, stock_data)
            #message sending
            producer.send(message.encode('utf-8'))
            #print message published
            print(f'Published to topic "stock-{stock_symbol}": {message}')
        #sleep
        time.sleep(60)  

#html interface
@app.route('/')
def index():
    """Serve the main page where the user can select a stock symbol."""
    return render_template('publisher.html')

#publish endpoint
@app.route('/publish', methods=['POST'])
def publish():
    """Handle stock symbol selection and start publishing data."""
    stock_symbol = request.form.get('stock_symbol')
    if stock_symbol:
        #create a thread for every time the endpoint is reached
        threading.Thread(target=publish_stock_data, args=(stock_symbol,), daemon=True).start()
        return jsonify({'status': 'success', 'message': f'Publishing stock data for {stock_symbol}'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Stock symbol is required'}), 400


if __name__ == '__main__':
    app.run(debug=True)
    client.close()
