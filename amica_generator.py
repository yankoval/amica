import hashlib
import xml.etree.ElementTree as ET
import os
import json
import re
import argparse
import csv

def calculate_md5(file_path):
    """Считает MD5 хеш файла для секции DataSource в VDF."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл данных не найден: {file_path}")
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest().upper()

def string_to_hex(text):
    """Кодирует строку в Hex-формат (UTF-8) для Amica."""
    return text.encode('utf-8').hex().upper()

def hex_to_string(hex_str):
    """Декодирует Hex-строку обратно в текст."""
    if not hex_str:
        return ""
    try:
        return bytes.fromhex(hex_str).decode('utf-8')
    except (ValueError, TypeError):
        return ""

def find_in_json(data, target_key):
    """Рекурсивный поиск значения по ключу в словаре любой вложенности."""
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

def generate_amica_vdf(base_template_path, new_csv_path, static_json_path, mapping_json_path, output_vdf_path):
    """Основная функция генерации VDF с подстановкой данных и исправлением параметров печати."""

    # 1. Подсчет количества строк в CSV (минус заголовок)
    if not os.path.exists(new_csv_path):
        raise FileNotFoundError(f"CSV файл не найден: {new_csv_path}")
    
    with open(new_csv_path, 'r', encoding='utf-8') as f:
        # Считаем строки, исключая пустые
        rows = [line for line in f if line.strip()]
        data_rows_count = len(rows) - 1 if len(rows) > 0 else 0

    # 2. Расчет MD5 и загрузка данных
    new_md5 = calculate_md5(new_csv_path)

    with open(static_json_path, 'r', encoding='utf-8') as f:
        static_data = json.load(f)

    with open(mapping_json_path, 'r', encoding='utf-8') as f:
        mapping_dict = json.load(f)

    # 3. Парсинг шаблона
    tree = ET.parse(base_template_path)
    root = tree.getroot()

    # 4. ОБРАТНЫЙ ИНЖИНИРИНГ: Обновление параметров RipParam (количество строк)
    rip_param = root.find(".//RipParam")
    if rip_param is not None:
        # Обновляем диапазон индексов (например, "0-9" для 10 строк)
        output_records = rip_param.find("OutputRecords")
        if output_records is not None:
            output_records.text = f"0-{max(0, data_rows_count - 1)}"
        
        # Обновляем общее количество (EndNo)
        end_no = rip_param.find("EndNo")
        if end_no is not None:
            end_no.text = str(data_rows_count)

    # Принудительно ставим 1 запись на этикетку
    consume_node = root.find(".//ConsumeRecordsPerPanel")
    if consume_node is not None:
        consume_node.text = "1"

    # 5. Обновление DataSource (путь к CSV и MD5)
    for data_source in root.findall(".//DataSource"):
        source_path_node = data_source.find(".//SourcePath")
        if source_path_node is not None:
            source_path_node.text = new_csv_path

        md5_node = data_source.find(".//DataMd5")
        if md5_node is not None:
            md5_node.text = new_md5

    # 6. Обновление статических текстовых блоков
    for content_node in root.findall(".//Content"):
        if content_node.text:
            decoded_text = hex_to_string(content_node.text)
            if not decoded_text:
                continue

            modified = False
            for json_key, text_in_template in mapping_dict.items():
                if text_in_template in decoded_text:
                    new_val = find_in_json(static_data, json_key)
                    if new_val is not None:
                        decoded_text = decoded_text.replace(text_in_template, str(new_val))
                        modified = True

            if modified:
                content_node.text = string_to_hex(decoded_text)

    # 7. Сохранение (short_empty_elements=False предотвращает появление <Content />)
    with open(output_vdf_path, 'wb') as f:
        tree.write(f, encoding="utf-8", xml_declaration=True, short_empty_elements=False)

    # 8. Финальная правка: оборачиваем в CDATA и чиним пустые теги
    with open(output_vdf_path, "r", encoding="utf-8") as f:
        xml_str = f.read()

    # Заменяем содержимое <Content>...</Content> на CDATA, включая пустые
    xml_str = re.sub(r'<Content[^>]*>(.*?)</Content>', r'<Content><![CDATA[\1]]></Content>', xml_str)
    
    # Дополнительная страховка для KeyField и других пустых тегов, если они важны
    xml_str = xml_str.replace('<KeyField></KeyField>', '<KeyField />')

    with open(output_vdf_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"---")
    print(f"[*] Файл успешно создан: {os.path.basename(output_vdf_path)}")
    print(f"[*] Записей к печати: {data_rows_count} (диапазон: 0-{max(0, data_rows_count-1)})")
    print(f"[*] MD5: {new_md5}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amica VDF Generator")
    parser.add_argument("--template", required=True, help="Путь к базовому шаблону VDF")
    parser.add_argument("--csv", required=True, help="Путь к новому CSV файлу")
    parser.add_argument("--json", required=True, help="Путь к JSON со статикой")
    parser.add_argument("--mapping", default="mapping.json", help="Путь к файлу маппинга")
    parser.add_argument("--output", required=True, help="Путь для сохранения результата")

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
        print(f"[!] Ошибка: {e}")
        exit(1)
