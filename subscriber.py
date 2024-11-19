import pulsar
import json
import threading
from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)

# Initialize SocketIO
socketio = SocketIO(app)

# Pulsar client setup
client = pulsar.Client('pulsar://localhost:6650')

# Shared data to store stock messages
stock_data_store = []

# Function to consume the data from topic
def consume_stock_data(topic_name):
    """Consume stock data from the selected Pulsar topic and store the received message."""
    #consumer initalization
    consumer = client.subscribe(topic_name, subscription_name='my-subscription', consumer_type=pulsar.ConsumerType.Exclusive)
    try:
        while True:
            # receive message
            msg = consumer.receive()  
            
            try:
                # Json coding
                stock_data = json.loads(msg.data().decode('utf-8'))
                print(f"Topic: {topic_name} - Current Price: {stock_data['price']}")  # Print only the price
                

                # Emit stock data to the client
                socketio.emit('stock_data', stock_data)

                # Store the stock data in memory
                stock_data_store.append(stock_data)
                # Acknowledge the message
                consumer.acknowledge(msg)  
            except Exception as e:
                print(f'Failed to process message: {e}')
                consumer.negative_acknowledge(msg)  # Send negative acknowledgment if there's an error
    except KeyboardInterrupt:
        print(f"Stopped receiving messages from topic: {topic_name}")
    finally:
        consumer.close()

#html interface
@app.route('/')
def index():
    """Render the HTML template where the user can select the topic to subscribe to."""
    return render_template('subscriber.html')


#subscribing endpoint
@app.route('/subscribe', methods=['POST'])
def subscribe():
    """Start subscribing to the selected topic and consume stock data."""
    # Get topic name from form submission
    topic_name = request.form.get('topic_name')  
    
    if topic_name:
        # Start the subscription process in a background thread
        threading.Thread(target=consume_stock_data, args=(topic_name,), daemon=True).start()
        return jsonify({'status': 'success', 'message': f'Subscription to topic: {topic_name} done!'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Topic name is required'}), 400

#endpoint to get stock data on the interface
@app.route('/get_stock_data', methods=['GET'])
def get_stock_data():
    """Return the latest stock data as JSON."""
    return jsonify(stock_data_store), 200

if __name__ == '__main__':
    # Start Flask-SocketIO server
    socketio.run(app, debug=True, port=5001)
    client.close()
