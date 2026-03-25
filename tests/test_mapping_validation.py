import pytest
import json
from amica_generator import generate_amica_vdf

def test_missing_placeholder_in_dict(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"

    mapping_content = {
        "article": {
            "transform": []
        }
    }
    mapping_file = tmp_path / "missing_placeholder.json"
    mapping_file.write_text(json.dumps(mapping_content))

    output = tmp_path / "output.vdf"

    with pytest.raises(ValueError, match="is missing required 'placeholder' field"):
        generate_amica_vdf(template, csv_data, static_json, str(mapping_file), str(output))

def test_duplicate_placeholders(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"

    mapping_content = {
        "article": "SAME_PLACEHOLDER",
        "other_key": {
            "placeholder": "SAME_PLACEHOLDER"
        }
    }
    mapping_file = tmp_path / "duplicate_placeholder.json"
    mapping_file.write_text(json.dumps(mapping_content))

    output = tmp_path / "output.vdf"

    with pytest.raises(ValueError, match="Duplicate placeholder 'SAME_PLACEHOLDER' found"):
        generate_amica_vdf(template, csv_data, static_json, str(mapping_file), str(output))
