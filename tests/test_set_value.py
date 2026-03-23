import pytest
import os
import xml.etree.ElementTree as ET
from amica_generator import generate_amica_vdf, hex_to_string

def test_set_value_in_mapping(tmp_path):
    # Template with a placeholder for a static value
    template_path = tmp_path / "template.vdf"
    # Placeholder for "GS" is hex "4753"
    template_path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<File Format="Amica.VDF">
  <VDPPage>
    <Page>
      <RipParam><EndNo>1</EndNo><OutputRecords>0-0</OutputRecords></RipParam>
      <DataSourceSet><DataSource><DataPathInfo><SourcePath>old.csv</SourcePath></DataPathInfo><DataMd5>OLDMD5</DataMd5></DataSource></DataSourceSet>
      <Content><![CDATA[4753]]></Content>
    </Page>
  </VDPPage>
</File>
""")

    csv_path = tmp_path / "data.csv"
    csv_path.write_text("header\nrecord1\n")

    # Static JSON (does NOT contain GS)
    json_path = tmp_path / "data.json"
    json_path.write_text('{"key": "val"}')

    # Mapping WITH setValue for GS
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('{"GS_key": {"placeholder": "GS", "setValue": "GS_VALUE"}}')

    output_path = tmp_path / "output.vdf"

    generate_amica_vdf(
        base_template_path=str(template_path),
        new_csv_path=str(csv_path),
        static_json_path=str(json_path),
        mapping_json_path=str(mapping_path),
        output_vdf_path=str(output_path)
    )

    assert os.path.exists(output_path)
    tree = ET.parse(output_path)
    root = tree.getroot()

    content_node = root.find(".//Content")
    assert content_node is not None
    decoded_text = hex_to_string(content_node.text)
    assert decoded_text == "GS_VALUE"

def test_missing_key_still_raises_error(tmp_path):
    template_path = tmp_path / "template.vdf"
    template_path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<File Format="Amica.VDF">
  <VDPPage>
    <Page>
      <RipParam><EndNo>1</EndNo><OutputRecords>0-0</OutputRecords></RipParam>
      <DataSourceSet><DataSource><DataPathInfo><SourcePath>old.csv</SourcePath></DataPathInfo><DataMd5>OLDMD5</DataMd5></DataSource></DataSourceSet>
      <Content><![CDATA[4753]]></Content>
    </Page>
  </VDPPage>
</File>
""")

    csv_path = tmp_path / "data.csv"
    csv_path.write_text("header\nrecord1\n")

    # Static JSON
    json_path = tmp_path / "data.json"
    json_path.write_text('{"key": "val"}')

    # Mapping refers to a missing key and has NO setValue
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('{"MISSING_KEY": {"placeholder": "GS"}}')

    output_path = tmp_path / "output.vdf"

    with pytest.raises(KeyError, match="not found in static JSON data"):
        generate_amica_vdf(
            base_template_path=str(template_path),
            new_csv_path=str(csv_path),
            static_json_path=str(json_path),
            mapping_json_path=str(mapping_path),
            output_vdf_path=str(output_path)
        )
