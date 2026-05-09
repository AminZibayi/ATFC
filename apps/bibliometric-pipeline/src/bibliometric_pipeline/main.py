"""
Convenience runner that executes all ETL stages in-process.
Note: this bypasses Nx caching — use `nx run bibliometric-pipeline:run` for
cached incremental execution.
"""
from bibliometric_pipeline.etl import extract, transform, load

def main():
    print("Starting Bibliometric Pipeline ETL...")
    extract.run()
    transform.run()
    load.run()
    print("\nETL Pipeline completed successfully.")

if __name__ == "__main__":
    main()