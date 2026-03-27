import pytest
import os
import json
import xml.etree.ElementTree as ET
from amica_generator import generate_amica_vdf, hex_to_string

def test_set_value_in_mapping(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"

    # Mapping with a setValue override
    mapping_content = [
        {
            "setValue": "FIXED_VALUE",
            "placeholder": "Placeholder_Article"
        }
    ]
    mapping_file = tmp_path / "set_value_mapping.json"
    mapping_file.write_text(json.dumps(mapping_content))

    output = tmp_path / "output_set_value.vdf"

    generate_amica_vdf(template, csv_data, static_json, str(mapping_file), str(output))

    assert os.path.exists(output)
    tree = ET.parse(output)
    root = tree.getroot()

    contents = []
    for content in root.findall(".//Content"):
        contents.append(hex_to_string(content.text))

    # "FIXED_VALUE" should replace Placeholder_Article instead of data from JSON
    assert "FIXED_VALUE" in contents

def test_missing_key_still_raises_error(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"

    # Mapping referring to missing key
    mapping_content = [{"MISSING_KEY": "some_placeholder"}]
    mapping_file = tmp_path / "missing_key.json"
    mapping_file.write_text(json.dumps(mapping_content))

    output = tmp_path / "output.vdf"

    with pytest.raises(KeyError):
        generate_amica_vdf(template, csv_data, static_json, str(mapping_file), str(output))
