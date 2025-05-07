# REST API: Uploads invoice image to 'inbox' and pushes message to RabbitMQ

import os
from flask import Flask, request, jsonify
import pika
from werkzeug.utils import secure_filename

# === Config ===
UPLOAD_FOLDER = 'inbox'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === Utility: File extension check ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === API Endpoint: POST /upload ===
@app.route('/upload', methods=['POST'])
def upload_file():
    # Step 1: Validate upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    # Step 2: Save file to inbox
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Step 3: Publish filename to RabbitMQ queue
    try:
        credentials = pika.PlainCredentials('user', 'pass')
        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq', credentials=credentials))
        channel = connection.channel()
        channel.queue_declare(queue='invoice_queue', durable=True)
        channel.basic_publish(
            exchange='',
            routing_key='invoice_queue',
            body=filename,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        return jsonify({'error': f'Failed to send to queue: {str(e)}'}), 500

    return jsonify({'message': f'{filename} uploaded and queued'}), 200

# === Flask Startup ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
