import json
import re
import zipfile
from pathlib import Path


def parse_las_file(file_path, encoding='utf-8'):
    las_data = {
        'Version': {},
        'Well': {},
        'Curve': {},
        'Parameter': {},
        'Other': '',
        'Ascii': []
    }

    section = None
    with open(file_path, 'r', encoding=encoding) as file:
        for line in file:
            line = line.strip()
            if line.startswith('~'):
                section_code = line[1]
                section = {
                    'V': 'Version',
                    'W': 'Well',
                    'C': 'Curve',
                    'P': 'Parameter',
                    'O': 'Other',
                    'A': 'Ascii'
                }.get(section_code, 'Other')

            elif section:
                if section in ['Version', 'Well', 'Curve', 'Parameter']:
                    match = re.match(r'^(\S+)\.(\S*)\s*:\s*(.*)', line)
                    if match:
                        key, unit, value = match.groups()
                        las_data[section][key.strip()] = {'unit': unit.strip(), 'value': value.strip()}
                elif section == 'Other':
                    las_data['Other'] += line + '\n'
                elif section == 'Ascii':
                    if line.strip():
                        values = line.split()
                        las_data['Ascii'].append(values)

    return las_data


zip_file_path = 'LAS.zip'
las_files_directory = Path('lasFiles')

las_files_directory.mkdir(exist_ok=True)


with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
    zip_ref.extractall(las_files_directory)

for las_file in las_files_directory.glob('*.LAS'):
    try:
        # сначала пробуем в utf-8
        parsed_data = parse_las_file(las_file)
    except UnicodeDecodeError:
        # Если utf-8 не подходит, пробуем прочитать в latin-1
        parsed_data = parse_las_file(las_file, encoding='latin-1')

    json_data = json.dumps(parsed_data, indent=4)
    json_file_name = las_file.with_suffix('.json')  # изменим расширение


    with open(json_file_name, 'w') as json_file:
        json_file.write(json_data)

    print(f"{las_file} конвертирован в {json_file_name}")
