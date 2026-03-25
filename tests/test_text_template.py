import os
import pytest
import xml.etree.ElementTree as ET
from amica_generator import generate_amica_vdf, hex_to_string, string_to_hex

def test_text_template_update(tmp_path):
    # Setup paths
    template_path = tmp_path / "template.vdf"
    csv_path = tmp_path / "data.csv"
    json_path = tmp_path / "data.json"
    mapping_path = tmp_path / "mapping.json"
    output_path = tmp_path / "output.vdf"

    # Create CSV
    csv_path.write_text("Header\nValue1", encoding="utf-8")
    # Create JSON
    json_path.write_text('{ "key1": "NEW_VALUE" }', encoding="utf-8")

    # Test Case 1: VariableText should use TextTemplate as source
    vdf_content = f"""<?xml version='1.0' encoding='utf-8'?>
<File Format="Amica.VDF" Version="3.0">
  <VDPPage Elements="1">
    <VariableText FullName="Amica.Vdp.Common.Element.VdpVariableText">
      <Text>
        <Content>{string_to_hex("OLD_CONTENT")}</Content>
      </Text>
      <TextTemplate>{string_to_hex("PLACEHOLDER_IN_TEMPLATE")}</TextTemplate>
    </VariableText>
    <Page FullName="Amica.Vdp.Common.Element.VdpPage">
      <RipParam FullName="Amica.Vdp.PageOutput.RipParam">
        <EndNo>1</EndNo>
        <OutputRecords>0-0</OutputRecords>
      </RipParam>
      <DataSourceSet DataCount="1">
        <DataSource>
          <DataPathInfo FullName="Amica.Vdp.Common.DataSource.CsvAdapter">
            <SourcePath>data.csv</SourcePath>
          </DataPathInfo>
          <DataMd5>HASH</DataMd5>
        </DataSource>
      </DataSourceSet>
    </Page>
  </VDPPage>
</File>"""
    template_path.write_text(vdf_content, encoding="utf-8")
    mapping_path.write_text('{ "key1": "PLACEHOLDER_IN_TEMPLATE" }', encoding="utf-8")

    generate_amica_vdf(str(template_path), str(csv_path), str(json_path), str(mapping_path), str(output_path))

    tree = ET.parse(output_path)
    root = tree.getroot()
    var_text = root.find(".//VariableText[@FullName='Amica.Vdp.Common.Element.VdpVariableText']")
    assert hex_to_string(var_text.find(".//Content").text) == "NEW_VALUE"
    assert hex_to_string(var_text.find("TextTemplate").text) == "NEW_VALUE"

    # Test Case 2: StaticText should still use Content as source
    vdf_content = f"""<?xml version='1.0' encoding='utf-8'?>
<File Format="Amica.VDF" Version="3.0">
  <VDPPage Elements="1">
    <StaticText FullName="Amica.Vdp.Common.Element.VdpStaticText">
      <Text>
        <Content>{string_to_hex("PLACEHOLDER_IN_CONTENT")}</Content>
      </Text>
      <TextTemplate>{string_to_hex("SHOULD_BE_IGNORED")}</TextTemplate>
    </StaticText>
    <Page FullName="Amica.Vdp.Common.Element.VdpPage">
      <RipParam FullName="Amica.Vdp.PageOutput.RipParam">
        <EndNo>1</EndNo>
        <OutputRecords>0-0</OutputRecords>
      </RipParam>
      <DataSourceSet DataCount="1">
        <DataSource>
          <DataPathInfo FullName="Amica.Vdp.Common.DataSource.CsvAdapter">
            <SourcePath>data.csv</SourcePath>
          </DataPathInfo>
          <DataMd5>HASH</DataMd5>
        </DataSource>
      </DataSourceSet>
    </Page>
  </VDPPage>
</File>"""
    template_path.write_text(vdf_content, encoding="utf-8")
    mapping_path.write_text('{ "key1": "PLACEHOLDER_IN_CONTENT" }', encoding="utf-8")

    generate_amica_vdf(str(template_path), str(csv_path), str(json_path), str(mapping_path), str(output_path))

    tree = ET.parse(output_path)
    root = tree.getroot()
    static_text = root.find(".//StaticText")
    assert hex_to_string(static_text.find(".//Content").text) == "NEW_VALUE"
    # TextTemplate of StaticText should NOT have been updated (it wasn't used as source and it's not VariableText)
    assert hex_to_string(static_text.find("TextTemplate").text) == "SHOULD_BE_IGNORED"
