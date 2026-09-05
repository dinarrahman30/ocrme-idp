from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        analytics_data = {
            "total_documents": 142,
            "categories": {
                "invoice": 58,
                "bank_statement": 34,
                "identity_card": 28,
                "receipt": 22
            },
            "average_accuracy": 97.4,
            "ai_utilization": 91.5,
            "ocr_engines": {
                "easyocr": 94,
                "tesseract": 48
            }
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(analytics_data).encode('utf-8'))
