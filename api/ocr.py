from http.server import BaseHTTPRequestHandler
import json
import cgi
import re

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Simple fallback JSON structure for demo / serverless OCR processing
            sample_data = {
                "metadata": {
                    "source_file": "document_uploaded.pdf",
                    "ocr_engine": "easyocr",
                    "parsing_method": "AUTO (LLM)",
                    "doc_type": "invoice",
                    "doc_subtype": "Faktur Penjualan",
                    "confidence": 0.96
                },
                "data": {
                    "invoice_number": "INV/2026/08/0091",
                    "date": "2026-08-20",
                    "customer": "PT Sumber Makmur Jaya",
                    "subtotal": 1500000.0,
                    "tax": 165000.0,
                    "total_amount": 1665000.0,
                    "transactions": [
                        {"item": "Layanan OCR Intelligent Processing", "qty": 1, "price": 1000000.0, "total": 1000000.0},
                        {"item": "Lisensi Serverless Deployment Vercel", "qty": 1, "price": 500000.0, "total": 500000.0}
                    ]
                }
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(sample_data).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "OCRMe API is active on Vercel"}).encode('utf-8'))
