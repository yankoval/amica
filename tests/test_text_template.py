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

    # 1. Create a minimal VDF template
    # One VariableText that should be updated
    # One VariableText that should NOT be updated (no match)
    # One StaticText (should not have TextTemplate updated even if content matches,
    # although StaticText usually doesn't have TextTemplate)

    vdf_content = f"""<?xml version='1.0' encoding='utf-8'?>
<File Format="Amica.VDF" Version="3.0">
  <VDPPage Elements="3">
    <VariableText FullName="Amica.Vdp.Common.Element.VdpVariableText">
      <Text>
        <Content>{string_to_hex("UPDATE_ME")}</Content>
      </Text>
      <TextTemplate>{string_to_hex("OLD_TEMPLATE")}</TextTemplate>
    </VariableText>
    <VariableText FullName="Amica.Vdp.Common.Element.VdpVariableText">
      <Text>
        <Content>{string_to_hex("KEEP_ME")}</Content>
      </Text>
      <TextTemplate>{string_to_hex("STAY_SAME")}</TextTemplate>
    </VariableText>
    <StaticText FullName="Amica.Vdp.Common.Element.VdpStaticText">
      <Text>
        <Content>{string_to_hex("UPDATE_ME")}</Content>
      </Text>
      <TextTemplate>{string_to_hex("OLD_TEMPLATE")}</TextTemplate>
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

    # 2. Create CSV
    csv_path.write_text("Header\nValue1", encoding="utf-8")

    # 3. Create JSON
    json_path.write_text('{ "key1": "NEW_VALUE" }', encoding="utf-8")

    # 4. Create Mapping
    mapping_path.write_text('{ "key1": "UPDATE_ME" }', encoding="utf-8")

    # 5. Run generator
    generate_amica_vdf(
        base_template_path=str(template_path),
        new_csv_path=str(csv_path),
        static_json_path=str(json_path),
        mapping_json_path=str(mapping_path),
        output_vdf_path=str(output_path)
    )

    # 6. Verify results
    tree = ET.parse(output_path)
    root = tree.getroot()

    elements = root.findall(".//VDPPage/*")

    # First element: VariableText, Content was "UPDATE_ME", should be "NEW_VALUE"
    # TextTemplate should also be hex("NEW_VALUE")
    var_text_1 = root.find(".//VariableText[@FullName='Amica.Vdp.Common.Element.VdpVariableText'][1]")
    content_1 = var_text_1.find(".//Content").text
    template_1 = var_text_1.find("TextTemplate").text

    assert hex_to_string(content_1) == "NEW_VALUE"
    assert template_1 == string_to_hex("NEW_VALUE")

    # Second element: VariableText, Content was "KEEP_ME", should remain same
    var_text_2 = root.findall(".//VariableText[@FullName='Amica.Vdp.Common.Element.VdpVariableText']")[1]
    content_2 = var_text_2.find(".//Content").text
    template_2 = var_text_2.find("TextTemplate").text

    assert hex_to_string(content_2) == "KEEP_ME"
    assert template_2 == string_to_hex("STAY_SAME")

    # Third element: StaticText, Content was "UPDATE_ME", should be "NEW_VALUE"
    # But TextTemplate should NOT be updated (or it doesn't matter, but rule says only for VariableText)
    static_text = root.find(".//StaticText")
    content_s = static_text.find(".//Content").text
    template_s = static_text.find("TextTemplate").text

    assert hex_to_string(content_s) == "NEW_VALUE"
    assert template_s == string_to_hex("OLD_TEMPLATE")
