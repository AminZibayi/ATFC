import urllib.request

from shared_python.paths import get_intermediate_data_path

AIO_URL = "https://raw.githubusercontent.com/berkeleybop/artificial-intelligence-ontology/main/aio.owl"


def fetch_vocabularies():
    print("=" * 70)
    print(" FETCHING VOCABULARIES")
    print("=" * 70)

    out_dir = get_intermediate_data_path("canonicalization-workflow", "vocabularies")
    out_dir.mkdir(parents=True, exist_ok=True)

    aio_path = out_dir / "aio.owl"
    if not aio_path.exists():
        print(f"Downloading AIO from {AIO_URL} ...")
        urllib.request.urlretrieve(AIO_URL, aio_path)
        print(f"Saved AIO to {aio_path}")
    else:
        print(f"AIO already exists at {aio_path}")


def run():
    fetch_vocabularies()


if __name__ == "__main__":
    run()
