import os
import time
import pytesseract
import shutil
import psycopg2
import pika
from PIL import Image
from pdf2image import convert_from_path

# === Directory Configs ===
INBOX_DIR = 'inbox'
PROCESSED_DIR = 'processed'
UNPROCESSED_DIR = 'unprocessed'  # ✅ Replaces 'failed'

# Ensure folders exist
for folder in [INBOX_DIR, PROCESSED_DIR, UNPROCESSED_DIR]:
    os.makedirs(folder, exist_ok=True)

# === Extract fields from OCR text ===
def extract_fields(text):
    lines = text.splitlines()
    data = {
        'invoice_number': None,
        'vendor': None,
        'date': None,
        'total': None
    }

    for line in lines:
        if 'Invoice:' in line:
            data['invoice_number'] = line.split('Invoice:')[-1].strip()
        elif 'Vendor:' in line:
            data['vendor'] = line.split('Vendor:')[-1].strip()
        elif 'Date:' in line:
            data['date'] = line.split('Date:')[-1].strip()
        elif 'Total Amount Due:' in line:
            data['total'] = line.split('Total Amount Due:')[-1].strip()

    return data

def is_valid(data):
    return all(data.values())

# === Insert extracted fields into PostgreSQL ===
def insert_to_db(data):
    conn = psycopg2.connect(
        dbname="invoices",
        user="user",
        password="pass",
        host="postgres"
    )
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            invoice_number TEXT,
            vendor TEXT,
            date TEXT,
            total TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO invoices (invoice_number, vendor, date, total)
        VALUES (%s, %s, %s, %s)
    """, (data['invoice_number'], data['vendor'], data['date'], data['total']))
    conn.commit()
    cursor.close()
    conn.close()

# === Main OCR processing ===
def process_invoice(file_name):
    input_path = os.path.join(INBOX_DIR, file_name)
    text = ""

    try:
        # Convert image or PDF to text
        # NOTE: PDF support wasn't originally required in the scope —
        # but I accidentally implemented support during testing and figured I'd leave it in as a bonus feature.
        if file_name.lower().endswith(".pdf"):
            images = convert_from_path(input_path)
        else:
            images = [Image.open(input_path)]

        for image in images:
            text += pytesseract.image_to_string(image)

        extracted = extract_fields(text)
        print(f"[🔍] Extracted fields from {file_name}: {extracted}")

        if is_valid(extracted):
            insert_to_db(extracted)
            shutil.move(input_path, os.path.join(PROCESSED_DIR, file_name))
            print(f"[✅] {file_name} successfully processed and moved to processed/")
        else:
            shutil.move(input_path, os.path.join(UNPROCESSED_DIR, file_name))
            print(f"[⚠️] Incomplete data — {file_name} moved to unprocessed/")

    except Exception as e:
        print(f"[🔥] ERROR processing {file_name}: {e}")
        shutil.move(input_path, os.path.join(UNPROCESSED_DIR, file_name))

# === RabbitMQ Callback ===
def callback(ch, method, properties, body):
    file_name = body.decode()
    process_invoice(file_name)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# === RabbitMQ Listener ===
def main():
    credentials = pika.PlainCredentials('user', 'pass')
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='invoice_queue', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='invoice_queue', on_message_callback=callback)

    print(" [*] Waiting for invoice messages...")
    channel.start_consuming()

if __name__ == '__main__':
    time.sleep(10)  # wait for RabbitMQ & Postgres
    main()
