import pytest
import os
import json
import xml.etree.ElementTree as ET
from amica_generator import generate_amica_vdf, hex_to_string, string_to_hex

def test_text_template_update(tmp_path):
    # Template with VariableText element
    template_path = tmp_path / "template.vdf"
    # Placeholder: Placeholder_Article
    placeholder_hex = string_to_hex("Placeholder_Article")
    template_path.write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<File Format="Amica.VDF">
  <VDPPage>
    <Page>
      <RipParam><EndNo>1</EndNo><OutputRecords>0-0</OutputRecords></RipParam>
      <DataSourceSet><DataSource><DataPathInfo><SourcePath>dummy.csv</SourcePath></DataPathInfo><DataMd5>DUMMYMD5</DataMd5></DataSource></DataSourceSet>
      <VariableText FullName="Amica.Vdp.Common.Element.VdpVariableText">
        <TextTemplate>{placeholder_hex}</TextTemplate>
        <Text>
          <Content>{placeholder_hex}</Content>
        </Text>
      </VariableText>
    </Page>
  </VDPPage>
</File>
""")

    csv_path = tmp_path / "data.csv"
    csv_path.write_text("header\nrecord1\n")

    # Static JSON
    json_path = tmp_path / "data.json"
    json_path.write_text('{"article": "ABC-123"}')

    # Mapping
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('[{"article": "Placeholder_Article"}]')

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

    var_text = root.find(".//VariableText")
    text_template = var_text.find("TextTemplate")
    content = var_text.find(".//Content")

    expected_hex = string_to_hex("ABC-123")
    assert text_template.text == expected_hex
    assert content.text == expected_hex
