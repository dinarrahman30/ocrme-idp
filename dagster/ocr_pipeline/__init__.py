from dagster import Definitions, load_assets_from_modules, EnvVar
from . import assets, resources

# Load all assets from assets.py module
all_assets = load_assets_from_modules([assets])

# Compile Dagster definitions with assets and resources
defs = Definitions(
    assets=all_assets,
    resources={
        "postgres_db": resources.PostgresResource(
            host="postgres",
            port=5432,
            user=EnvVar("POSTGRES_USER"),
            password=EnvVar("POSTGRES_PASSWORD"),
            database=EnvVar("POSTGRES_DB")
        ),
        "minio_storage": resources.MinIOResource(
            endpoint=EnvVar("MINIO_ENDPOINT"),
            access_key=EnvVar("MINIO_ROOT_USER"),
            secret_key=EnvVar("MINIO_ROOT_PASSWORD")
        )
    }
)
