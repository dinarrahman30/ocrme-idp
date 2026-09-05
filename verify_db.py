import sqlite3
import pandas as pd

DB_PATH = "data/ocr_database.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    
    print("====================================================")
    print("           DATABASE VERIFICATION RESULTS            ")
    print("====================================================")
    
    # 1. Processed Files Log
    print("\n[1] File Processing Log:")
    try:
        df_log = pd.read_sql_query("SELECT * FROM processed_files", conn)
        print(df_log.to_string(index=False) if not df_log.empty else "Empty log.")
    except Exception as e:
        print(f"Error reading processed_files: {e}")
        
    # 2. KTP Records
    print("\n[2] KTP Records:")
    try:
        df_ktp = pd.read_sql_query("SELECT id, file_path, nik, nama, tempat_tgl_lahir, pekerjaan FROM ktp_records", conn)
        print(df_ktp.to_string(index=False) if not df_ktp.empty else "Empty table.")
    except Exception as e:
        print(f"Error reading ktp_records: {e}")
        
    # 3. Bank Transactions
    print("\n[3] Bank Transactions (Top 10):")
    try:
        df_tx = pd.read_sql_query("SELECT id, file_path, date, description, amount, type, balance FROM bank_transactions LIMIT 10", conn)
        print(df_tx.to_string(index=False) if not df_tx.empty else "Empty table.")
        
        # Transaction stats
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN type='CR' THEN amount ELSE 0 END), SUM(CASE WHEN type='DB' THEN amount ELSE 0 END) FROM bank_transactions")
        count, total_cr, total_db = cursor.fetchone()
        print(f"\nStats: Total Transactions = {count or 0}, Total CR = {total_cr or 0:.2f}, Total DB = {total_db or 0:.2f}")
    except Exception as e:
        print(f"Error reading bank_transactions: {e}")

    # 4. Generic Document Records (LLM-parsed)
    print("\n[4] Document Records (LLM-Parsed) — Top 10:")
    try:
        df_docs = pd.read_sql_query(
            "SELECT id, file_path, doc_type, doc_subtype, parsing_method, confidence, processed_at "
            "FROM document_records ORDER BY processed_at DESC LIMIT 10", conn
        )
        if not df_docs.empty:
            print(df_docs.to_string(index=False))
            
            # Count by type
            cursor = conn.cursor()
            cursor.execute("SELECT doc_type, parsing_method, COUNT(*) FROM document_records GROUP BY doc_type, parsing_method")
            rows = cursor.fetchall()
            if rows:
                print("\nSummary by Type & Method:")
                for doc_type, method, count in rows:
                    print(f"  {doc_type} ({method}): {count} records")
        else:
            print("Empty table.")
    except Exception as e:
        print(f"Error reading document_records: {e}")
        
    conn.close()
    print("\n====================================================")

if __name__ == "__main__":
    main()
