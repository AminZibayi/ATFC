from shared_python.paths import (
    DATA_DIR,
    get_intermediate_data_path,
    get_output_path,
    get_plot_path,
    get_raw_data_path,
)


def test_shared_paths_under_data_root():
    assert get_raw_data_path("sample.xlsx").parts[-3:] == ("data", "raw", "sample.xlsx")
    assert get_intermediate_data_path("demo", "items.csv").parts[-4:] == ("data", "intermediate", "demo", "items.csv")
    assert get_output_path("demo", "result.json").parts[-4:] == ("data", "outputs", "demo", "result.json")
    assert get_plot_path("demo", "plot.png").parts[-5:] == ("data", "outputs", "demo", "plots", "plot.png")
    assert DATA_DIR.name == "data"
