from dagster import ConfigurableResource
import psycopg2
import boto3
from botocore.client import Config
import logging

class PostgresResource(ConfigurableResource):
    host: str
    port: int
    user: str
    password: str
    database: str

    def get_connection(self):
        """Returns a psycopg2 database connection."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.database
            )
            return conn
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise e

class MinIOResource(ConfigurableResource):
    endpoint: str
    access_key: str
    secret_key: str

    def get_client(self):
        """Returns a boto3 s3 client configured for MinIO."""
        try:
            return boto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_key_id=self.secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1' # dummy region for MinIO
            )
        except Exception as e:
            logging.error(f"Failed to connect to MinIO: {str(e)}")
            raise e
