from bibliometric_pipeline.etl import extract, transform, load

def main():
    print("Starting Bibliometric Pipeline ETL...")
    extract.run()
    transform.run()
    load.run()
    print("\nETL Pipeline completed successfully.")

if __name__ == "__main__":
    main()