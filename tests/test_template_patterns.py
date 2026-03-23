import os
import pytest
import xml.etree.ElementTree as ET
import json
from amica_generator import generate_amica_vdf, hex_to_string, string_to_hex

def test_template_patterns(tmp_path):
    # Setup temporary files
    template_path = tmp_path / "template.vdf"
    csv_path = tmp_path / "data.csv"
    json_path = tmp_path / "static.json"
    mapping_path = tmp_path / "mapping.json"
    output_path = tmp_path / "output.vdf"

    # Template with {Key} pattern
    # <<C1>>01{Product_PackBarcode}10{Batch_BN_1C_full}
    content_text = "<<C1>>01{Product_PackBarcode}10{Batch_BN_1C_full}"
    content_hex = string_to_hex(content_text)

    template_content = f"""<?xml version="1.0" encoding="utf-8"?>
<Vdf>
    <DataSource>
        <SourcePath>dummy.csv</SourcePath>
        <DataMd5>DUMMY</DataMd5>
    </DataSource>
    <Content>{content_hex}</Content>
</Vdf>
"""
    template_path.write_text(template_content)
    csv_path.write_text("dummy")

    mapping_data = {
        "Product_PackBarcode": "PPB_PLACEHOLDER",
        "Batch_BN_1C_full": "BATCH_PLACEHOLDER"
    }
    mapping_path.write_text(json.dumps(mapping_data))

    static_data = {
        "Product_PackBarcode": "1234567890",
        "Batch_BN_1C_full": "BN123"
    }
    json_path.write_text(json.dumps(static_data))

    generate_amica_vdf(
        base_template_path=str(template_path),
        new_csv_path=str(csv_path),
        static_json_path=str(json_path),
        mapping_json_path=str(mapping_path),
        output_vdf_path=str(output_path)
    )

    assert os.path.exists(output_path)
    tree = ET.parse(output_path)
    content_node = tree.find(".//Content")
    decoded_output = hex_to_string(content_node.text)

    # Expected: <<C1>>01123456789010BN123
    assert decoded_output == "<<C1>>01123456789010BN123"

def test_template_patterns_missing_key_in_mapping(tmp_path):
    template_path = tmp_path / "template.vdf"
    csv_path = tmp_path / "data.csv"
    json_path = tmp_path / "static.json"
    mapping_path = tmp_path / "mapping.json"
    output_path = tmp_path / "output.vdf"

    content_text = "{MissingKey}"
    content_hex = string_to_hex(content_text)

    template_content = f"<Vdf><DataSource><SourcePath>x</SourcePath><DataMd5>x</DataMd5></DataSource><Content>{content_hex}</Content></Vdf>"
    template_path.write_text(template_content)
    csv_path.write_text("x")
    mapping_path.write_text(json.dumps({}))
    json_path.write_text(json.dumps({}))

    with pytest.raises(KeyError):
        generate_amica_vdf(
            base_template_path=str(template_path),
            new_csv_path=str(csv_path),
            static_json_path=str(json_path),
            mapping_json_path=str(mapping_path),
            output_vdf_path=str(output_path)
        )

def test_template_patterns_with_transformations(tmp_path):
    template_path = tmp_path / "template.vdf"
    csv_path = tmp_path / "data.csv"
    json_path = tmp_path / "static.json"
    mapping_path = tmp_path / "mapping.json"
    output_path = tmp_path / "output.vdf"

    content_text = "Date: {Batch_Date}"
    content_hex = string_to_hex(content_text)

    template_content = f"<Vdf><DataSource><SourcePath>x</SourcePath><DataMd5>x</DataMd5></DataSource><Content>{content_hex}</Content></Vdf>"
    template_path.write_text(template_content)
    csv_path.write_text("x")

    # Mapping with transformation
    mapping_data = {
        "Batch_Date": {
            "placeholder": "DATE_PLACEHOLDER",
            "transform": [
                {"type": "strptime", "format": "%Y-%m-%d"},
                {"type": "strftime", "format": "%d.%m.%Y"}
            ]
        }
    }
    mapping_path.write_text(json.dumps(mapping_data))

    static_data = {"Batch_Date": "2023-10-27"}
    json_path.write_text(json.dumps(static_data))

    generate_amica_vdf(
        base_template_path=str(template_path),
        new_csv_path=str(csv_path),
        static_json_path=str(json_path),
        mapping_json_path=str(mapping_path),
        output_vdf_path=str(output_path)
    )

    tree = ET.parse(output_path)
    content_node = tree.find(".//Content")
    decoded_output = hex_to_string(content_node.text)

    # Expected: Date: 27.10.2023
    assert decoded_output == "Date: 27.10.2023"

def test_template_patterns_missing_key_in_static(tmp_path):
    template_path = tmp_path / "template.vdf"
    csv_path = tmp_path / "data.csv"
    json_path = tmp_path / "static.json"
    mapping_path = tmp_path / "mapping.json"
    output_path = tmp_path / "output.vdf"

    content_text = "{KeyInMapping}"
    content_hex = string_to_hex(content_text)

    template_content = f"<Vdf><DataSource><SourcePath>x</SourcePath><DataMd5>x</DataMd5></DataSource><Content>{content_hex}</Content></Vdf>"
    template_path.write_text(template_content)
    csv_path.write_text("x")
    mapping_path.write_text(json.dumps({"KeyInMapping": "Value"}))
    json_path.write_text(json.dumps({})) # Missing in static data

    with pytest.raises(KeyError):
        generate_amica_vdf(
            base_template_path=str(template_path),
            new_csv_path=str(csv_path),
            static_json_path=str(json_path),
            mapping_json_path=str(mapping_path),
            output_vdf_path=str(output_path)
        )
