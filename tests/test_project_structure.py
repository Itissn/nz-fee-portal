from pathlib import Path


def test_required_files_exist():
    root = Path(__file__).resolve().parents[1]

    assert (root / "app" / "streamlit_app.py").exists()
    assert (root / "requirements.txt").exists()
    assert (root / "README.md").exists()


def test_data_folder_exists():
    root = Path(__file__).resolve().parents[1]

    assert (root / "data").exists()