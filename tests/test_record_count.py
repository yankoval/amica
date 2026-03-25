import pytest
import os
import json
import xml.etree.ElementTree as ET
from amica_generator import generate_amica_vdf

def test_cdata_wrapping_of_empty_content(tmp_path):
    # Template with empty Content tag
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

    # Static JSON
    json_path = tmp_path / "data.json"
    json_path.write_text('{"key": "val"}')

    # Mapping
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('[{"key": "placeholder"}]')

    output_path = tmp_path / "output.vdf"

    generate_amica_vdf(
        base_template_path=str(template_path),
        new_csv_path=str(csv_path),
        static_json_path=str(json_path),
        mapping_json_path=str(mapping_path),
        output_vdf_path=str(output_path)
    )

    assert os.path.exists(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        xml_str = f.read()

    # Empty content should be <Content><![CDATA[]]></Content>
    assert "<Content><![CDATA[]]></Content>" in xml_str

def test_record_count_calculation(tmp_path):
    # CSV with 3 data records
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("header\nrec1\nrec2\nrec3\n")

    template_path = tmp_path / "template.vdf"
    template_path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<File>
  <RipParam><EndNo>1</EndNo><OutputRecords>0-0</OutputRecords></RipParam>
</File>
""")

    # We need dummy JSON and mapping to call generate_amica_vdf
    json_path = tmp_path / "data.json"
    json_path.write_text('{}')
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('[]')

    output_path = tmp_path / "output.vdf"

    generate_amica_vdf(str(template_path), str(csv_path), str(json_path), str(mapping_path), str(output_path))

    tree = ET.parse(output_path)
    root = tree.getroot()

    assert root.find(".//EndNo").text == "3"
    assert root.find(".//OutputRecords").text == "0-2"

def test_record_count_empty_file_raises_error(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("header\n\n") # Only header and empty line

    template_path = tmp_path / "template.vdf"
    template_path.write_text("<File><RipParam><EndNo>0</EndNo></RipParam></File>")

    json_path = tmp_path / "data.json"
    json_path.write_text('{}')
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('[]')

    output_path = tmp_path / "output.vdf"

    with pytest.raises(ValueError, match="contains no records"):
        generate_amica_vdf(str(template_path), str(csv_path), str(json_path), str(mapping_path), str(output_path))
