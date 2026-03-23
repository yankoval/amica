import pytest
import os
import xml.etree.ElementTree as ET
from amica_generator import generate_amica_vdf, hex_to_string, string_to_hex

def test_braced_placeholder_replacement(tmp_path):
    # Template with braced placeholders {Batch_number} and {GS}
    # {Batch_number} -> 7b42617463685f6e756d6265727d
    # {GS} -> 7b47537d
    template_path = tmp_path / "template.vdf"
    template_path.write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<File Format="Amica.VDF">
  <VDPPage>
    <Page>
      <RipParam><EndNo>1</EndNo><OutputRecords>0-0</OutputRecords></RipParam>
      <DataSourceSet><DataSource><DataPathInfo><SourcePath>old.csv</SourcePath></DataPathInfo><DataMd5>OLDMD5</DataMd5></DataSource></DataSourceSet>
      <Content><![CDATA[{string_to_hex("Batch: {Batch_number}, GS: {GS_key}")}]]></Content>
    </Page>
  </VDPPage>
</File>
""")

    csv_path = tmp_path / "data.csv"
    csv_path.write_text("header\nrecord1\n")

    # Static JSON
    json_path = tmp_path / "data.json"
    json_path.write_text('{"Batch_number": "BATCH123"}')

    # Mapping
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('{"Batch_number": "BATCH_PLACEHOLDER", "GS_key": {"setValue": "GS_VALUE"}}')

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
    # Both {Batch_number} and {GS_key} should be replaced
    assert decoded_text == "Batch: BATCH123, GS: GS_VALUE"
