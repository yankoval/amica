import os
import json
import pytest
from amica_generator import generate_amica_vdf, hex_to_string
import xml.etree.ElementTree as ET

def test_zfill_transformation(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = tmp_path / "test_data_zfill.json"
    mapping = tmp_path / "test_mapping_zfill.json"
    output = tmp_path / "output_zfill.vdf"

    # Create test data with a short barcode
    static_data = {
        "Product_PackBarcode": "1234567890123" # 13 digits
    }
    with open(static_json, 'w', encoding='utf-8') as f:
        json.dump(static_data, f)

    # Create mapping with zfill transformation
    mapping_data = {
        "Product_PackBarcode": {
            "placeholder": "Product_PackBarcode",
            "transform": [
                {
                    "type": "zfill",
                    "width": 14
                }
            ]
        }
    }
    with open(mapping, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f)

    # We need a template that has "Product_PackBarcode" in it.
    # Let's use the existing test_template.vdf but it might not have Product_PackBarcode.
    # We can check if it has any placeholder we can swap for testing.

    # Create a simple template with our placeholder in hex
    placeholder_hex = "Product_PackBarcode".encode('utf-8').hex().upper()
    template_content = f"""<?xml version="1.0" encoding="utf-8"?>
<VdfFile>
    <DataSourceSet>
        <DataSource>
            <SourcePath>DUMMY.CSV</SourcePath>
            <DataMd5>DUMMY_MD5</DataMd5>
        </DataSource>
    </DataSourceSet>
    <RipParam>
        <EndNo>1</EndNo>
        <OutputRecords>0-0</OutputRecords>
    </RipParam>
    <Label>
        <Content>{placeholder_hex}</Content>
    </Label>
</VdfFile>"""

    test_template = tmp_path / "test_zfill.vdf"
    test_template.write_text(template_content, encoding='utf-8')

    generate_amica_vdf(str(test_template), csv_data, str(static_json), str(mapping), str(output))

    assert os.path.exists(output)

    # Parse output VDF
    tree = ET.parse(output)
    root = tree.getroot()

    contents = []
    for content in root.findall(".//Content"):
        contents.append(hex_to_string(content.text))

    # "1234567890123" with zfill(14) -> "01234567890123"
    assert "01234567890123" in contents

def test_zfill_missing_width(tmp_path):
    template = "tests/data/test_template.vdf"
    csv_data = "tests/data/test_dummy.csv"
    static_json = tmp_path / "test_data.json"
    mapping = tmp_path / "test_mapping.json"
    output = tmp_path / "output.vdf"

    static_data = {"key": "val"}
    with open(static_json, 'w', encoding='utf-8') as f:
        json.dump(static_data, f)

    mapping_data = {
        "key": {
            "placeholder": "placeholder",
            "transform": [{"type": "zfill"}]
        }
    }
    with open(mapping, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f)

    with pytest.raises(ValueError, match="Missing 'width' for zfill transformation"):
        generate_amica_vdf(template, csv_data, str(static_json), str(mapping), str(output))
