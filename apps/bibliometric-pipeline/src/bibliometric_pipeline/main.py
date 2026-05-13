"""
Convenience runner that executes all ETL stages in-process.
Note: this bypasses Nx caching — use `nx run bibliometric-pipeline:run` for
cached incremental execution.
"""
from bibliometric_pipeline.etl import extract, build_graphs, apply_layout

def main():
    print("Starting Bibliometric Pipeline ETL...")
    extract.run()
    build_graphs.run()
    apply_layout.run()
    print("\nETL Pipeline completed successfully.")

if __name__ == "__main__":
    main()