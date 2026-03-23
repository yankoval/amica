import pytest
import os
import xml.etree.ElementTree as ET
from amica_generator import count_csv_rows, generate_amica_vdf

def test_count_csv_rows(tmp_path):
    # Case 1: 1 header + 5 records
    csv_file = tmp_path / "test1.csv"
    csv_file.write_text("header\nrecord1\nrecord2\nrecord3\nrecord4\nrecord5\n")
    assert count_csv_rows(str(csv_file)) == 5

    # Case 2: 1 header + 1 record
    csv_file = tmp_path / "test2.csv"
    csv_file.write_text("header\nrecord1\n")
    assert count_csv_rows(str(csv_file)) == 1

    # Case 3: Only header (0 records) -> should raise ValueError
    csv_file = tmp_path / "test3.csv"
    csv_file.write_text("header\n")
    with pytest.raises(ValueError, match="contains no records"):
        count_csv_rows(str(csv_file))

    # Case 4: Empty file -> should raise ValueError
    csv_file = tmp_path / "test4.csv"
    csv_file.write_text("\n\n")
    with pytest.raises(ValueError, match="contains no records"):
        count_csv_rows(str(csv_file))

def test_rip_param_update(tmp_path):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    template_path = os.path.join(base_dir, "tests", "data", "DM_100_GLOBAL_Label.VDF")
    json_path = os.path.join(base_dir, "tests", "data", "BN000806463.json")
    mapping_path = os.path.join(base_dir, "mapping.json")

    # Create a CSV with 3 records (+ 1 header)
    csv_path = tmp_path / "records.csv"
    csv_path.write_text("ID\n1\n2\n3\n")

    output_path = tmp_path / "output.vdf"

    generate_amica_vdf(
        base_template_path=template_path,
        new_csv_path=str(csv_path),
        static_json_path=json_path,
        mapping_json_path=mapping_path,
        output_vdf_path=str(output_path)
    )

    assert os.path.exists(output_path)

    # Parse output and check RipParam
    tree = ET.parse(output_path)
    root = tree.getroot()

    rip_param = root.find(".//RipParam")
    assert rip_param is not None

    end_no = rip_param.find("EndNo").text
    assert end_no == "3"

    output_records = rip_param.find("OutputRecords").text
    assert output_records == "0-2"

def test_cdata_wrapping_of_empty_content(tmp_path):
    # Create a dummy template with an empty Content tag
    template_path = tmp_path / "template.vdf"
    template_path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<File Format="Amica.VDF">
  <VDPPage>
    <Page>
      <RipParam><EndNo>1</EndNo><OutputRecords>0-0</OutputRecords></RipParam>
      <DataSourceSet><DataSource><DataPathInfo><SourcePath>old.csv</SourcePath></DataPathInfo><DataMd5>OLDMD5</DataMd5></DataSource></DataSourceSet>
      <Content></Content>
    </Page>
  </VDPPage>
</File>
""")

    csv_path = tmp_path / "data.csv"
    csv_path.write_text("header\nrecord1\n")

    # Dummy static json and mapping
    json_path = tmp_path / "data.json"
    json_path.write_text('{"key": "val"}')
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('{"key": "val"}')

    output_path = tmp_path / "output.vdf"

    generate_amica_vdf(
        base_template_path=str(template_path),
        new_csv_path=str(csv_path),
        static_json_path=str(json_path),
        mapping_json_path=str(mapping_path),
        output_vdf_path=str(output_path)
    )

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Verify CDATA wrapping even for empty Content
        assert "<Content><![CDATA[]]></Content>" in content
