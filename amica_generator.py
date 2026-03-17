import hashlib
import xml.etree.ElementTree as ET
import os
import json
import re
import argparse

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
    """Кодирует строку в Hex-формат UTF-8 для Amica."""
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

def count_csv_rows(csv_path):
    """Считает количество строк данных в CSV (исключая заголовок)."""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = [line for line in f if line.strip()]
            return max(0, len(lines) - 1)
    except Exception:
        return 0

def generate_amica_vdf(base_template_path, new_csv_path, static_json_path, mapping_json_path, output_vdf_path):
    """Основная функция генерации VDF с подстановкой данных и обновлением счетчиков."""
    
    # 1. Считаем количество записей и MD5
    record_count = count_csv_rows(new_csv_path)
    new_md5 = calculate_md5(new_csv_path)

    # 2. Загружаем данные
    with open(static_json_path, 'r', encoding='utf-8') as f:
        static_data = json.load(f)
        
    with open(mapping_json_path, 'r', encoding='utf-8') as f:
        mapping_dict = json.load(f)

    # 3. Парсим VDF шаблон
    tree = ET.parse(base_template_path)
    root = tree.getroot()

    # 4. ОБНОВЛЕНИЕ СЧЕТЧИКОВ (чтобы не открывалось с "4")
    # Ищем параметры RipParam для установки диапазона печати
    rip_param = root.find(".//RipParam")
    if rip_param is not None:
        # Устанавливаем конечное число записей
        end_no = rip_param.find("EndNo")
        if end_no is not None:
            end_no.text = str(record_count)
            
        # Устанавливаем диапазон (например, "0-99" для 100 записей)
        out_records = rip_param.find("OutputRecords")
        if out_records is not None:
            out_records.text = f"0-{max(0, record_count - 1)}"

    # 5. Обновляем динамическую часть (путь к CSV и MD5)
    for data_source in root.findall(".//DataSource"):
        source_path_node = data_source.find(".//SourcePath")
        if source_path_node is not None:
            source_path_node.text = new_csv_path
            
        md5_node = data_source.find(".//DataMd5")
        if md5_node is not None:
            md5_node.text = new_md5

    # 6. Обновляем статическую часть (Текстовые блоки)
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

    # 7. Сохраняем результат (short_empty_elements=False для корректных тегов Content)
    tree.write(output_vdf_path, encoding="utf-8", xml_declaration=True, short_empty_elements=False)
    
    # 8. Финальный штрих: оборачиваем Hex-текст в CDATA
    with open(output_vdf_path, "r", encoding="utf-8") as f:
        xml_str = f.read()
        
    # Улучшенная регулярка: обрабатывает и заполненные, и пустые теги Content
    xml_str = re.sub(r'<Content[^>]*>(.*?)</Content>', r'<Content><![CDATA[\1]]></Content>', xml_str)
    
    with open(output_vdf_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"---")
    print(f"[*] Файл успешно создан: {os.path.basename(output_vdf_path)}")
    print(f"[*] Найдено записей в CSV: {record_count}")
    print(f"[*] MD5: {new_md5}")

if __name__ == "__main__":
    # Для запуска через CLI можно добавить argparse, но пока оставим ваши пути
    TMPL = r"C:\tmp\DM_100_GLOBAL_Label.VDF"
    try:
        generate_amica_vdf(
            base_template_path=TMPL,
            new_csv_path=os.path.abspath(r"C:\tmp\SSCC_2026-02-16_tst.txt"), 
            static_json_path=r"C:\tmp\BN000806463.json",
            mapping_json_path=r"C:\tmp\mapping.json",
            output_vdf_path=r"C:\tmp\BN000806463.vdf"
            )
    except Exception as e:
        print(f"[!] Ошибка: {e}")
