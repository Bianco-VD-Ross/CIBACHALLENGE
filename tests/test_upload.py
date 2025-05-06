# tests/test_upload.py
# Purpose: Basic integration test for Flask upload endpoint

import os
import requests

def test_upload_sample_invoice():
    url = "http://localhost:5000/upload"
    sample_path = "samples/invoice_1.png"

    # Ensure the sample file exists
    assert os.path.exists(sample_path), f"❌ File not found: {sample_path}"

    with open(sample_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(url, files=files)

    # Validate response
    assert response.status_code == 200, f"❌ Unexpected status code: {response.status_code}"
    response_json = response.json()

    # Verify message structure
    assert "message" in response_json, "❌ 'message' key missing from response"
    print(f"✅ Upload test passed: {response_json['message']}")

if __name__ == '__main__':
    test_upload_sample_invoice()
