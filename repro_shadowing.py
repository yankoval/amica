import json
import os
import xml.etree.ElementTree as ET
from amica_generator import generate_amica_vdf, hex_to_string, string_to_hex

def test_shadowing_fix():
    # Setup files
    template_path = "shadow_template.vdf"
    csv_path = "shadow_data.csv"
    json_path = "shadow_data.json"
    mapping_path = "shadow_mapping.json"
    output_path = "shadow_output.vdf"

    # User's case: overlapping placeholders
    mapping_data = [
        {
            "date": {
                "placeholder": "Batch_date_production",
                "setValue": "DATE_SHORT"
            }
        },
        {
            "date": {
                "placeholder": "Batch_date_production_mY",
                "setValue": "DATE_LONG"
            }
        }
    ]
    with open(mapping_path, "w") as f:
        json.dump(mapping_data, f)

    with open(json_path, "w") as f:
        json.dump({"date": "any"}, f)

    with open(csv_path, "w") as f:
        f.write("h\nd\n")

    # Template content with both literal and braced versions
    template_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<File Format="Amica.VDF">
  <DataSourceSet><DataSource><SourcePath>x</SourcePath><DataMd5>y</DataMd5></DataSource></DataSourceSet>
  <RipParam><EndNo>1</EndNo><OutputRecords>0-0</OutputRecords></RipParam>
  <Label>
    <Content>{string_to_hex("Batch_date_production")}</Content>
    <Content>{string_to_hex("Batch_date_production_mY")}</Content>
    <Content>{string_to_hex("Braced: {Batch_date_production_mY} and {Batch_date_production}")}</Content>
  </Label>
</File>"""
    with open(template_path, "w") as f:
        f.write(template_xml)

    try:
        generate_amica_vdf(template_path, csv_path, json_path, mapping_path, output_path)

        tree = ET.parse(output_path)
        contents = [hex_to_string(c.text) for c in tree.findall(".//Content")]

        # Exact match tests
        assert contents[0] == "DATE_SHORT"
        assert contents[1] == "DATE_LONG"

        # Braced replacement tests (length-sorted sorting prevents shadowing)
        assert contents[2] == "Braced: DATE_LONG and DATE_SHORT"

        print("Shadowing fix verification: SUCCESS!")

    finally:
        # Cleanup
        for f in [template_path, csv_path, json_path, mapping_path, output_path]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    test_shadowing_fix()
