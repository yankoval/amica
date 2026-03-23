import os
import pytest
from amica_generator import generate_amica_vdf, hex_to_string
import xml.etree.ElementTree as ET

def test_transformations(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"
    mapping = "tests/data/test_mapping.json"
    output = tmp_path / "output.vdf"

    generate_amica_vdf(template, csv_data, static_json, mapping, str(output))

    assert os.path.exists(output)

    # Parse output VDF
    tree = ET.parse(output)
    root = tree.getroot()

    contents = []
    for content in root.findall(".//Content"):
        contents.append(hex_to_string(content.text))

    # "ABC-123" with regex "^[A-Z]+-" -> "123"
    assert "123" in contents
    # "2026-03-15" with strptime "%Y-%m-%d" and strftime "%m.%Y" -> "03.2026"
    assert "03.2026" in contents

    # Check RipParam updates
    # test_dummy.csv has 5 lines
    end_no = root.find(".//RipParam/EndNo")
    assert end_no is not None
    assert end_no.text == "5"

    out_records = root.find(".//RipParam/OutputRecords")
    assert out_records is not None
    assert out_records.text == "0-4"

def test_missing_key(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"
    # mapping refers to a key that doesn't exist in test_data.json
    mapping_content = '{"non_existent": {"placeholder": "Placeholder_Article"}}'
    mapping_file = tmp_path / "missing_key_mapping.json"
    mapping_file.write_text(mapping_content)

    output = tmp_path / "output.vdf"

    with pytest.raises(KeyError):
        generate_amica_vdf(template, csv_data, static_json, str(mapping_file), str(output))

def test_invalid_transformation(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"
    # invalid date format
    mapping_content = '{"batch_date": {"placeholder": "Date_Placeholder", "transform": [{"type": "strptime", "format": "%d-%m-%Y"}]}}'
    mapping_file = tmp_path / "invalid_trans_mapping.json"
    mapping_file.write_text(mapping_content)

    output = tmp_path / "output.vdf"

    with pytest.raises(ValueError):
        generate_amica_vdf(template, csv_data, static_json, str(mapping_file), str(output))

def test_backward_compatibility(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"
    # Old format: key-to-placeholder
    mapping_content = '{"article": "Placeholder_Article"}'
    mapping_file = tmp_path / "old_mapping.json"
    mapping_file.write_text(mapping_content)

    output = tmp_path / "output_old.vdf"

    generate_amica_vdf(template, csv_data, static_json, str(mapping_file), str(output))

    assert os.path.exists(output)
    tree = ET.parse(output)
    root = tree.getroot()

    contents = []
    for content in root.findall(".//Content"):
        contents.append(hex_to_string(content.text))

    assert "ABC-123" in contents

def test_filename_mask(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = "tests/data/test_data.json"
    mapping = "tests/data/test_mapping.json"
    output = tmp_path / "original.vdf"

    mask = "{article}_{OriginalFileName}"
    # article in test_data.json is "ABC-123", transform regex "^[A-Z]+-" -> "123"

    generate_amica_vdf(template, csv_data, static_json, mapping, str(output), filename_mask=mask)

    expected_path = tmp_path / "123_original.vdf"
    assert os.path.exists(expected_path)
    # Original output path should NOT exist because it was renamed/saved as mask
    assert not os.path.exists(output)
