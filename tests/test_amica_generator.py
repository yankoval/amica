import os
import pytest
import xml.etree.ElementTree as ET
from amica_generator import calculate_md5, generate_amica_vdf, hex_to_string

def test_calculate_md5(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "hello.txt"
    p.write_text("hello world")

    # MD5 of "hello world" is 5EB63BBBE01EEED093CB22BB8F5ACDC3
    expected_md5 = "5EB63BBBE01EEED093CB22BB8F5ACDC3"
    assert calculate_md5(str(p)) == expected_md5

def test_generate_amica_vdf():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    template_path = os.path.join(base_dir, "tests", "data", "DM_100_GLOBAL_Label.VDF")
    csv_path = os.path.join(base_dir, "tests", "data", "SSCC_2026-02-16_tst.txt")
    json_path = os.path.join(base_dir, "tests", "data", "BN000806463.json")
    mapping_path = os.path.join(base_dir, "mapping.json")
    expected_path = os.path.join(base_dir, "tests", "data", "BN000806463.vdf")
    output_path = "test_output.vdf"

    try:
        generate_amica_vdf(
            base_template_path=template_path,
            new_csv_path=csv_path,
            static_json_path=json_path,
            mapping_json_path=mapping_path,
            output_vdf_path=output_path
        )

        assert os.path.exists(output_path)

        # Parse both files
        tree_out = ET.parse(output_path)
        tree_exp = ET.parse(expected_path)

        root_out = tree_out.getroot()
        root_exp = tree_exp.getroot()

        # Check MD5 in DataSource
        md5_out = root_out.find(".//DataMd5").text
        expected_md5 = calculate_md5(csv_path)
        assert md5_out == expected_md5

        # Compare Content tags
        contents_out = root_out.findall(".//Content")
        contents_exp = root_exp.findall(".//Content")

        assert len(contents_out) == len(contents_exp)

        for c_out, c_exp in zip(contents_out, contents_exp):
            # We compare decoded strings because Hex might differ in case or something,
            # though our generator uses upper().
            # Note: Expected VDF might have some tags we didn't touch.
            val_out = hex_to_string(c_out.text)
            val_exp = hex_to_string(c_exp.text)
            assert val_out == val_exp

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
