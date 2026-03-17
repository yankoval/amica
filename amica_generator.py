import hashlib
import xml.etree.ElementTree as ET
import os
import json
import re
import argparse
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Setup logging
logger = logging.getLogger("amica_generator")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler("amica_generator.log", maxBytes=1*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def calculate_md5(file_path):
    """Calculates MD5 hash of a file for the DataSource section in VDF."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest().upper()

def string_to_hex(text):
    """Encodes string to Hex format (UTF-8) for Amica."""
    return text.encode('utf-8').hex().upper()

def hex_to_string(hex_str):
    """Decodes Hex string back to text."""
    if not hex_str:
        return ""
    try:
        return bytes.fromhex(hex_str).decode('utf-8')
    except (ValueError, TypeError):
        return ""

def find_in_json(data, target_key):
    """Recursively search for a value by key in a dictionary of any nesting."""
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for v in data.values():
            res = find_in_json(v, target_key)
            if res is not None:
                return res
    elif isinstance(data, list):
        for item in data:
            res = find_in_json(item, target_key)
            if res is not None:
                return res
    return None

def apply_transformations(value, transformations):
    """Applies a list of transformations to a value."""
    current_value = value
    for trans in transformations:
        trans_type = trans.get("type")
        try:
            if trans_type == "strptime":
                fmt = trans.get("format")
                if not fmt:
                    raise ValueError("Missing 'format' for strptime transformation")
                current_value = datetime.strptime(current_value, fmt)
            elif trans_type == "strftime":
                fmt = trans.get("format")
                if not fmt:
                    raise ValueError("Missing 'format' for strftime transformation")
                if not isinstance(current_value, datetime):
                    raise TypeError(f"strftime expected datetime object, got {type(current_value)}")
                current_value = current_value.strftime(fmt)
            elif trans_type == "regex":
                pattern = trans.get("pattern")
                replacement = trans.get("replacement")
                if pattern is None or replacement is None:
                    raise ValueError("Missing 'pattern' or 'replacement' for regex transformation")
                current_value = re.sub(pattern, replacement, str(current_value))
            else:
                raise ValueError(f"Unknown transformation type: {trans_type}")
        except Exception as e:
            logger.error(f"Transformation failed: {trans}. Value: {current_value}. Error: {e}")
            raise
    return current_value

def generate_amica_vdf(base_template_path, new_csv_path, static_json_path, mapping_json_path, output_vdf_path):
    """Main function to generate VDF by substituting static and dynamic data."""

    # 1. Calculate MD5 of the new CSV file
    new_md5 = calculate_md5(new_csv_path)

    # 2. Load data
    with open(static_json_path, 'r', encoding='utf-8') as f:
        static_data = json.load(f)

    with open(mapping_json_path, 'r', encoding='utf-8') as f:
        mapping_dict = json.load(f)

    # 3. Parse VDF template (XML)
    tree = ET.parse(base_template_path)
    root = tree.getroot()

    # 4. Update dynamic part (CSV path and MD5)
    for data_source in root.findall(".//DataSource"):
        source_path_node = data_source.find(".//SourcePath")
        if source_path_node is not None:
            # We keep the path provided in arguments, but Amica might expect Windows paths.
            # However, for testing purpose and general use, we use the provided path.
            source_path_node.text = new_csv_path

        md5_node = data_source.find(".//DataMd5")
        if md5_node is not None:
            md5_node.text = new_md5

    # 5. Update static part (Text blocks)
    for content_node in root.findall(".//Content"):
        if content_node.text:
            decoded_text = hex_to_string(content_node.text)
            if not decoded_text:
                continue

            modified = False
            # Check each rule from mapping
            for json_key, mapping_info in mapping_dict.items():
                if isinstance(mapping_info, dict):
                    text_in_template = mapping_info.get("placeholder")
                    transformations = mapping_info.get("transform", [])
                else:
                    text_in_template = mapping_info
                    transformations = []

                if text_in_template and text_in_template in decoded_text:
                    new_val = find_in_json(static_data, json_key)
                    if new_val is None:
                        error_msg = f"Key '{json_key}' not found in static JSON data"
                        logger.error(error_msg)
                        raise KeyError(error_msg)

                    if transformations:
                        new_val = apply_transformations(new_val, transformations)

                    decoded_text = decoded_text.replace(text_in_template, str(new_val))
                    modified = True

            if modified:
                content_node.text = string_to_hex(decoded_text)

    # 6. Save the result
    # short_empty_elements=False ensures <Content></Content> instead of <Content />
    with open(output_vdf_path, 'wb') as f:
        tree.write(f, encoding="utf-8", xml_declaration=True, short_empty_elements=False)

    # 7. Final touch: wrap Hex text (or empty) in CDATA
    with open(output_vdf_path, "r", encoding="utf-8") as f:
        xml_str = f.read()

    # Replace content of <Content>...</Content> with CDATA
    xml_str = re.sub(r'<Content[^>]*>(.*?)</Content>', r'<Content><![CDATA[\1]]></Content>', xml_str)

    # Handle self-closing tags just in case
    xml_str = xml_str.replace('<Content />', '<Content><![CDATA[]]></Content>')

    with open(output_vdf_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    logger.info(f"---")
    logger.info(f"[*] File successfully created: {os.path.basename(output_vdf_path)}")
    logger.info(f"[*] Used CSV: {os.path.basename(new_csv_path)}")
    logger.info(f"[*] MD5: {new_md5}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amica VDF Generator")
    parser.add_argument("--template", required=True, help="Path to base VDF template")
    parser.add_argument("--csv", required=True, help="Path to new CSV/data file")
    parser.add_argument("--json", required=True, help="Path to static JSON data")
    parser.add_argument("--mapping", default="mapping.json", help="Path to mapping JSON file")
    parser.add_argument("--output", required=True, help="Path for the output VDF file")

    args = parser.parse_args()

    try:
        generate_amica_vdf(
            base_template_path=args.template,
            new_csv_path=args.csv,
            static_json_path=args.json,
            mapping_json_path=args.mapping,
            output_vdf_path=args.output
        )
    except Exception as e:
        logger.exception(f"[!] Error: {e}")
        print(f"[!] Error: {e}")
        exit(1)
