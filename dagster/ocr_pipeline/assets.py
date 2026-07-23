import os
import tempfile
import logging
from dagster import asset, AssetExecutionContext

# Import existing local OCR and parsing utilities
from src.prepocessing import clean_image
from src.ocr_engine import image_to_text, process_pdf
from src.parser import parse_bca_statement, parse_ktp

@asset(required_resource_keys={"minio_storage"})
def raw_documents(context: AssetExecutionContext) -> list:
    """Lists files in the 'input-documents' bucket in MinIO."""
    minio = context.resources.minio_storage.get_client()
    
    try:
        response = minio.list_objects_v2(Bucket="input-documents")
        files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                ext = os.path.splitext(key.lower())[1]
                if ext in [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
                    files.append(key)
                    
        context.log.info(f"Found {len(files)} raw documents in MinIO.")
        return files
    except Exception as e:
        context.log.error(f"Failed to list MinIO files: {str(e)}")
        return []

@asset(required_resource_keys={"minio_storage"}, non_argument_deps={"raw_documents"})
def ocr_extracted_text(context: AssetExecutionContext) -> dict:
    """Runs OCR on the documents and uploads raw extracted text to the 'extracted-text' bucket."""
    minio = context.resources.minio_storage.get_client()
    
    try:
        response = minio.list_objects_v2(Bucket="input-documents")
        if "Contents" not in response:
            context.log.info("No documents to process in raw bucket.")
            return {}
    except Exception as e:
        context.log.error(f"Failed to check input-documents bucket: {str(e)}")
        return {}
        
    ocr_results = {}
    
    # Check already processed texts in extracted-text bucket to avoid redundant runs
    try:
        extracted_response = minio.list_objects_v2(Bucket="extracted-text")
        already_extracted = set()
        if "Contents" in extracted_response:
            already_extracted = {obj["Key"] for obj in extracted_response["Contents"]}
    except Exception:
        already_extracted = set()

    for obj in response["Contents"]:
        key = obj["Key"]
        base_name, ext = os.path.splitext(key)
        ext = ext.lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            continue
            
        txt_key = f"hasil_{base_name}.txt"
        if txt_key in already_extracted:
            context.log.info(f"Skipping OCR for {key}, text already exists in object storage.")
            ocr_results[key] = txt_key
            continue

        # Download to a temporary file to run local OCR
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            minio.download_file("input-documents", key, temp_path)
            context.log.info(f"Running OCR on {key}...")
            
            # Default to easyocr for table/layout structure preservation
            if ext == ".pdf":
                extracted_text = process_pdf(temp_path, dpi=200, engine="easyocr")
            else:
                clean_img = clean_image(temp_path)
                extracted_text = image_to_text(clean_img, lang="ind+eng", engine="easyocr")
                
            # Upload extracted text to MinIO
            minio.put_object(
                Bucket="extracted-text",
                Key=txt_key,
                Body=extracted_text.encode("utf-8")
            )
            context.log.info(f"Uploaded extracted text for {key} to MinIO as {txt_key}")
            ocr_results[key] = txt_key
        except Exception as e:
            context.log.error(f"Failed to process OCR for {key}: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return ocr_results

@asset(required_resource_keys={"minio_storage", "postgres_db"}, non_argument_deps={"ocr_extracted_text"})
def parsed_database_records(context: AssetExecutionContext):
    """Parses extracted text files from MinIO and loads structured records into PostgreSQL."""
    minio = context.resources.minio_storage.get_client()
    postgres_resource = context.resources.postgres_db
    
    # 1. Initialize Tables in PostgreSQL
    conn = postgres_resource.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            file_path TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            error_message TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ktp_records (
            id SERIAL PRIMARY KEY,
            file_path TEXT,
            nik TEXT,
            nama TEXT,
            tempat_tgl_lahir TEXT,
            jenis_kelamin TEXT,
            alamat TEXT,
            rt_rw TEXT,
            kel_desa TEXT,
            kecamatan TEXT,
            agama TEXT,
            status_perkawinan TEXT,
            pekerjaan TEXT,
            kewarganegaraan TEXT,
            berlaku_hingga TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id SERIAL PRIMARY KEY,
            file_path TEXT,
            date TEXT,
            description TEXT,
            amount DOUBLE PRECISION,
            type TEXT,
            balance DOUBLE PRECISION,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    # 2. Get list of already loaded files in PostgreSQL
    cursor.execute("SELECT file_path FROM processed_files WHERE status = 'SUCCESS'")
    success_loaded = {row[0] for row in cursor.fetchall()}
    
    # 3. Read extracted text files and parse them
    try:
        response = minio.list_objects_v2(Bucket="extracted-text")
        if "Contents" not in response:
            context.log.info("No extracted texts found in MinIO.")
            cursor.close()
            conn.close()
            return
    except Exception as e:
        context.log.error(f"Failed to list extracted-text bucket: {str(e)}")
        cursor.close()
        conn.close()
        return
        
    for obj in response["Contents"]:
        txt_key = obj["Key"]
        # Map back to original document path in input-documents
        base_name = txt_key.replace("hasil_", "").replace(".txt", "")
        
        # Check original file in input-documents to construct exact key
        orig_key = None
        try:
            input_response = minio.list_objects_v2(Bucket="input-documents")
            if "Contents" in input_response:
                for input_obj in input_response["Contents"]:
                    if os.path.splitext(input_obj["Key"])[0] == base_name:
                        orig_key = input_obj["Key"]
                        break
        except Exception:
            pass
                    
        if not orig_key:
            orig_key = f"{base_name}.pdf" # fallback
            
        if orig_key in success_loaded:
            context.log.info(f"Skipping database load for {orig_key}, already loaded.")
            continue
            
        context.log.info(f"Downloading extracted text: {txt_key}")
        try:
            txt_obj = minio.get_object(Bucket="extracted-text", Key=txt_key)
            extracted_text = txt_obj["Body"].read().decode("utf-8")
        except Exception as e:
            context.log.error(f"Failed to download extracted text {txt_key}: {str(e)}")
            continue
        
        text_lower = extracted_text.lower()
        is_ktp = "ktp" in base_name.lower() or "nik" in text_lower
        is_bca = "bca" in base_name.lower() or "mutasi" in text_lower or "saldo" in text_lower
        
        try:
            if is_ktp:
                context.log.info(f"Parsing KTP data from: {orig_key}")
                parsed_data = parse_ktp(extracted_text)
                
                cursor.execute("""
                    INSERT INTO ktp_records (
                        file_path, nik, nama, tempat_tgl_lahir, jenis_kelamin, alamat, 
                        rt_rw, kel_desa, kecamatan, agama, status_perkawinan, 
                        pekerjaan, kewarganegaraan, berlaku_hingga
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    orig_key,
                    parsed_data.get("nik"),
                    parsed_data.get("nama"),
                    parsed_data.get("tempat_tgl_lahir"),
                    parsed_data.get("jenis_kelamin"),
                    parsed_data.get("alamat"),
                    parsed_data.get("rt_rw"),
                    parsed_data.get("kel_desa"),
                    parsed_data.get("kecamatan"),
                    parsed_data.get("agama"),
                    parsed_data.get("status_perkawinan"),
                    parsed_data.get("pekerjaan"),
                    parsed_data.get("kewarganegaraan"),
                    parsed_data.get("berlaku_hingga")
                ))
                
            elif is_bca:
                context.log.info(f"Parsing BCA Statement transactions from: {orig_key}")
                parsed_data = parse_bca_statement(extracted_text)
                
                for tx in parsed_data:
                    cursor.execute("""
                        INSERT INTO bank_transactions (
                            file_path, date, description, amount, type, balance
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        orig_key,
                        tx.get("date"),
                        tx.get("description"),
                        tx.get("amount"),
                        tx.get("type"),
                        tx.get("balance")
                    ))
            else:
                context.log.warning(f"Unknown document format for {orig_key}. Skipping structured parse.")
                cursor.execute("""
                    INSERT INTO processed_files (file_path, status, error_message)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (file_path) DO UPDATE SET status = EXCLUDED.status, error_message = EXCLUDED.error_message
                """, (orig_key, "SUCCESS", "Parsed as generic/unknown format"))
                conn.commit()
                continue
                
            cursor.execute("""
                INSERT INTO processed_files (file_path, status)
                VALUES (%s, %s)
                ON CONFLICT (file_path) DO UPDATE SET status = EXCLUDED.status, error_message = NULL
            """, (orig_key, "SUCCESS"))
            conn.commit()
            context.log.info(f"Successfully parsed and loaded {orig_key} to PostgreSQL.")
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Parsing or Database loading failed: {str(e)}"
            context.log.error(error_msg)
            cursor.execute("""
                INSERT INTO processed_files (file_path, status, error_message)
                VALUES (%s, %s, %s)
                ON CONFLICT (file_path) DO UPDATE SET status = EXCLUDED.status, error_message = EXCLUDED.error_message
            """, (orig_key, "FAILED", error_msg))
            conn.commit()
            
    cursor.close()
    conn.close()
