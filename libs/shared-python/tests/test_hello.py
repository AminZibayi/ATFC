from shared_python.paths import (
    DATA_DIR,
    get_intermediate_data_path,
    get_output_path,
    get_plot_path,
    get_raw_data_path,
)


def test_shared_paths_under_data_root():
    assert str(get_raw_data_path("sample.xlsx")).endswith(r"data\raw\sample.xlsx")
    assert str(get_intermediate_data_path("demo", "items.csv")).endswith(r"data\intermediate\demo\items.csv")
    assert str(get_output_path("demo", "result.json")).endswith(r"data\outputs\demo\result.json")
    assert str(get_plot_path("demo", "plot.png")).endswith(r"data\outputs\demo\plots\plot.png")
    assert DATA_DIR.name == "data"
