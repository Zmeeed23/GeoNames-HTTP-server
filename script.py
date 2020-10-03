import re
import sqlite3
import requests
import socket

# Символы для реализации псевдоперевода с транслита на кириллицу
chars = {'a': 'а', 'b': 'б', 'c': 'ц', 'd': 'д', 'e': 'е', 'ë': 'ё', 'f': 'ф', 'g': 'г', 'h': 'х', 'i': 'и', 'j': 'й', 'k': 'к',
    'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'v': 'в', 'w': 'в', 'y': 'ы',
    'z': 'з', '”': 'ъ', '"': 'ъ', '’': 'ь', '\'': 'ь'}

# Эмпирический подбор сочетаний символов для устранения псевдоперевода
sets = {'ые': 'е', 'ыё': 'ё', 'ыо': 'ё', 'ыи': 'ьи', 'зх': 'ж', 'кх': 'х', 'тс': 'ц', 'цх': 'ч', 'сх': 'ш', 'ыу': 'ю',
    'ыа': 'я', 'иы': 'ий', 'оы': 'ой', 'ыы': 'ый', 'скы': 'ский', 'ыйе': 'ые', 'етц': 'ец', 'цч': 'щ', 'аы': 'ай',
    'цкы': 'тский', 'еы': 'ей', 'уы': 'уй', 'оы': 'ой', 'юы': 'юй', 'ёы': 'ёй', 'хоф': 'гоф'}

# Набор кодов для их замены названиями регионов. Коды взяты по адресу: http://download.geonames.org/export/dump/admin1CodesASCII.txt
regions = {'01': 'Адыгея', '03': 'Алтай', '08': 'Башкортостан', '11': 'Бурятия', '17': 'Дагестан', '19': 'Ингушетия',
    '22': 'Кабардино-Балкария', '24': 'Калмыкия', '27': 'Карачаево-Черкесия', '28': 'Карелия', '34': 'Коми', '45': 'Марий Эл',
    '46': 'Мордовия', '63': 'Якутия', '68': 'Северная Осетия', '73': 'Татарстан', '79': 'Тыва', '80': 'Удмуртия', '31': 'Хакасия',
    '12': 'Чечня', '16': 'Чувашия', '04': 'Алтайский', '93': 'Забайкальский', '92': 'Камчатский', '38': 'Краснодарский',
    '91': 'Красноярский', '90': 'Пермский', '59': 'Приморский', '70': 'Ставропольский', '30': 'Хабаровский', '05': 'Амурская',
    '06': 'Архангельская', '07': 'Астраханская', '09': 'Белгородская', '10': 'Брянская', '83': 'Владимирская', '84': 'Волгоградская',
    '85': 'Вологодская', '86': 'Воронежская', '21': 'Ивановская', '20': 'Иркутская', '23': 'Калининградская', '25': 'Калужская',
    '29': 'Кемеровская', '33': 'Кировская', '37': 'Костромская', '40': 'Курганская', '41': 'Курская', '42': 'Ленинградская',
    '43': 'Липецкая', '44': 'Магаданская', '47': 'Московская', '49': 'Мурманская', '51': 'Нижегородская', '53': 'Новосибирская',
    '54': 'Омская', '55': 'Оренбургская', '56': 'Орловская', '57': 'Пензенская', '60': 'Псковская', '61': 'Ростовская', '62': 'Рязанская',
    '65': 'Самарская', '67': 'Саратовская', '64': 'Сахалинская', '71': 'Свердловская', '69': 'Смоленская', '72': 'Тамбовская',
    '77': 'Тверская', '75': 'Томская', '76': 'Тульская', '78': 'Тюменская', '81': 'Ульяновская', '13': 'Челябинская', '88': 'Ярославская',
    '48': 'Москва', '66': 'Санкт-Петербург', '89': 'Еврейская автономная область', '50': 'Ненецкий автономный округ',
    '32': 'Ханты-Мансийский автономный округ', '15': 'Чукотский автономный округ', '87': 'Ямало-Ненецкий автономный округ'}

# Функция, выполняющая перевод названия населённого пункта с транслита на кириллицу
def translation(name):
    for char in name:
        if char in chars:
            cyr = chars.get(char)
            name = name.replace(char, cyr)
    for cyr in sets:
        if 'схцх' in name:
            name = name.replace('схцх', 'щ')
        if cyr in name:
            letter = sets.get(cyr)
            name = name.replace(cyr, letter)
    return name

# Функция, заполняющая текстом все поля, содержащие None
def null_replacement(info):
    info = ['Нет данных' if i is None else i for i in info]
    return info

# Функция, редактирующая поле временной зоны населённого пункта
def timezone_correction(tz):
    if '-1' in tz:
        tz = 'МСК' + tz
    elif '0' in tz:
        tz = 'МСК'
    else:
        tz = 'МСК+' + tz
    return tz

if __name__ == '__main__':

    print('Запуск сервера...')

    # Создание таблицы резидентной базы данных с информацией о населённых пунктах
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute("""CREATE TABLE places(
        geonameid VARCHAR(10) PRIMARY KEY,
        name VARCHAR(200),
        alternatenames VARCHAR(10000),
        latitude VARCHAR(15),
        longitude VARCHAR(15),
        admin1_code VARCHAR(30),
        admin2_code VARCHAR(80),
        population VARCHAR(8),
        elevation VARCHAR(5),
        timezone VARCHAR(50),
        modification_date VARCHAR(10));""")
    conn.commit()

    # Чтение данных из RU.txt, их обработка и запись в таблицу
    with open('RU.txt', 'r') as file:
        while True:
            line = file.readline()

            # По невыясненной причине, информация о Москве и Санкт-Петербурге не подходит под шаблон регулярного выражения,
            # которое обрабатывает строки с информацией о населённых пунктах, вследствие чего обработка реализована без
            # использования регулярных выражений следующим образом:

            # Обработка информации о Санкт-Петербурге
            if '498817' in line:
                res = [i for i in line.rstrip('\n').split('\t') if i]
                row = (res[0], res[1], res[3], res[4], res[5], res[9], None, res[10], res[11], res[12], res[13])
                cur.execute("INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", row)
                conn.commit()

            # Обработка информации о Москве
            if '524901' in line:
                res = [i for i in line.rstrip('\n').split('\t') if i]
                row = (res[0], res[1], res[3], res[4], res[5], res[9], None, res[10], res[11], res[12], res[13])
                cur.execute("INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", row)
                conn.commit()

            # Обработка информации об остальных населённых пунктах
            # Так как законодательство РФ не определяет город как населённый пункт, численность населения которого превышает некоторое
            # определённое значение, и так как в RU.txt нет чёткого разделения населённых пунктов на типы, то для определённости
            # отфильтрованы населённые пункты, у которых численность населения указана равной 0, и классификация которых в базе данных
            # GeoNames логически не соответствует городам
            if re.search(r'\tPPL\t|\tPPL[^FLXR]\t', line) and re.search(r'\t+[^0\t]+\t+[-?\d]+\t+\w+/[\w-]+', line):
                fields = re.match(r'(\d+)\t+([^\t]+)\t+[^\t]*\t+([^\t]+)?\t+([\d\.]+)\t+([-\d\.]+)\t+P\t+\w{3,4}\t+RU\t+\w*,*\t+([^\t]+)?\t+([^\t]+)?\t+[^\t]*\t+[^\t]*\t+(\d+)\t+([-?\d]+)\t+(\w+/[\w-]+)\t+(\d{4}-\d{2}-\d{2})\n', line)
                cur.execute("INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", fields.groups())
                conn.commit()
            if not line:
                break

    # Перевод названий населённых пунктов с транслита на русский
    names = []
    for line in cur.execute("SELECT name, geonameid FROM places;"):
        name = line[0].lower()
        id = line[1]
        name = translation(name)

        # Редактирование некоторых нешаблонных названий
        if 'уелен' in name:
            name = name.replace('уе', 'уэ')
        if 'ессо' in name:
            name = name.replace('е', 'э')
        if 'камчацк' in name:
            name = name.replace('ц', 'тс')
        if 'иркуцк' in name:
            name = name.replace('ц', 'тс')
        if 'тюмен' in name:
            name = name.replace('н', 'нь')
        if 'няган' in name:
            name = name.replace('ан', 'ань')
        if 'електро' in name:
            name = name.replace('ел', 'эл')
        if 'елиста' in name:
            name = name.replace('ел', 'эл')
        if 'мосцов' in name:
            name = name.replace('мосцов', 'москва')
        if 'саинт' in name:
            name = name.replace('саинт петерсбург', 'санкт-петербург')
        if re.match(r'ен', name):
            name = name.replace('ен', 'эн')
        name = name.title()
        if '-Он-' in name:
            name = name.replace('-Он-', '-на-')
        result = (name, id)
        names.append(result)

    # Внесение изменений в таблицу
    cur.executemany("UPDATE places SET name = ? WHERE geonameid = ?;", names)
    conn.commit()
    del names

    # Чтение данных по указанному адресу и их обработка для редактирования полей временной зоны
    t_z = requests.get('http://download.geonames.org/export/dump/timeZones.txt')
    times = t_z.text.split('\n')
    timezones = []
    for line in times:
        dataset = re.match(r'RU\t(\w+/[-\w ]+)\t(\d{1,2})', line)
        try:
            timezones.append(list(dataset.groups()))
        except AttributeError:
            pass
    for dataset in timezones:
        dataset[1] = str(int(dataset[1])-3)
        dataset.reverse()

    # Внесение изменений в таблицу
    cur.executemany("UPDATE places SET timezone = ? WHERE timezone = ?;", timezones)
    conn.commit()
    del timezones
    del times
    del t_z

    # Редактирование полей региона (субъекта РФ)
    subjects = []
    for code in regions:
        name = regions.get(code)
        if name.endswith('ская'):
            name = name.replace('ская', 'ская область')
        if name.endswith('ский'):
            name = name.replace('ский', 'ский край')
        dataset = (name, code)
        subjects.append(dataset)

    # Внесение изменений в таблицу
    cur.executemany("UPDATE places SET admin1_code = ? WHERE admin1_code = ?;", subjects)
    conn.commit()
    del subjects

    # Чтение данных по указанному адресу и их обработка для редактирования полей района (округа)
    ds = requests.get('http://download.geonames.org/export/dump/admin2Codes.txt')
    district = ds.text.split('\n')
    districts = []
    for line in district:
        dataset = re.match(r'RU\.\d{2}\.(\d+)\t([\w -]+)\t', line)
        try:
            id = dataset.group(1)
            name = dataset.group(2).lower()
            name = translation(name)
        except AttributeError:
            pass
        else:

            # Редактирование некоторых нешаблонных названий
            if 'раён' in name:
                name = name.replace('раён', 'район')
            if 'урбан' in name:
                name = name.replace('урбан', 'городской')
            if 'дистрицт' in name:
                name = name.replace('дистрицт', 'округ')
            if 'натионал' in name:
                name = name.replace('натионал', 'национальный')
            if 'циты' in name:
                name = name.replace('циты', 'город')
            if 'републицан' in name:
                name = name.replace('републицан', 'республиканский')
            if 'административе' in name:
                name = name.replace('административе', 'административный')
            if 'еастерн' in name:
                name = name.replace('еастерн', 'восточный')
            if 'нижны' in name:
                name = name.replace('нижны', 'нижний')
            if 'елиста' in name:
                name = name.replace('елиста', 'элиста')
            if 'грозны' in name:
                name = name.replace('грозны', 'грозный')
            if 'рецк' not in name:
                name = name.replace('цк', 'тск')
            name = name.capitalize()
            result = (name, id)
            districts.append(result)

    # Внесение изменений в таблицу
    cur.executemany("UPDATE places SET admin2_code = ? WHERE admin2_code = ?;", districts)
    conn.commit()
    del districts
    del district
    del ds

    # Инициализация серверного сокета
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 8000))
    server.listen()
    print('Сервер запущен')

    # Обработка клиентских запросов
    while True:
        client, _ = server.accept()
        while True:
            client.send("""\nВыберите действие:
1 - Вывести информацию о населённом пункте по его идентификатору;
2 - Вывести произвольный список населённых пунктов с информацией о них;
3 - Вывести информацию о двух населённых пунктах и сравнить их широту и временную зону;
4 - Ввести часть названия населённого пункта и вывести возможные варианты продолжений;
q - Отключиться от сервера.
Выбор: """.encode())
            request = client.recv(4).decode().rstrip('\n')

            # Обработка первого метода
            if '1' == request:
                client.send('\nВведите id искомого населённого пункта: '.encode())
                request = (client.recv(32).decode().rstrip('\n'),)
                cur.execute("SELECT * FROM places WHERE geonameid = ?;", request)
                try:
                    info = list(cur.fetchone())
                    info = null_replacement(info)
                    info[-2] = timezone_correction(info[-2])
                except TypeError:
                    client.send('\nОшибка ввода или населённого пункта по заданному идентификатору не существует.\n'.encode())
                else:
                    client.send("""\nРезультат поиска:\n
Населённый пункт: {}
Другие названия: {}
Широта: {}
Долгота: {}
Субъект: {}
Район: {}
Население: {}
Высота НУМ: {}
Временная зона: {}
Данные по состоянию на {}\n""".format(info[1], info[2], info[3], info[4], info[5],
info[6], info[7], info[8], info[9], info[10]).encode())

            # Обработка второго метода
            elif '2' == request:
                errors = True
                while errors:
                    try:
                        client.send('\nВведите количество населённых пунктов на странице: '.encode())
                        amount = int(client.recv(16).decode().rstrip('\n'))
                        client.send('\nВведите номер страницы: '.encode())
                        page_number = int(client.recv(16).decode().rstrip('\n'))
                        if amount <= 0 or page_number <= 0:
                            raise ValueError
                    except ValueError:
                        client.send('\nОшибка ввода!\n'.encode())
                    else:
                        errors = False
                content = []
                for i in cur.execute("SELECT * FROM places;"):
                    page = cur.fetchmany(size=amount)
                    content.append(page)
                try:
                    client.send('\nРезультат поиска:\n'.encode())
                    for line in content[page_number - 1]:
                        line = null_replacement(line)
                        line[-2] = timezone_correction(line[-2])
                        client.send("""
Населённый пункт: {}
Другие названия: {}
Широта: {}
Долгота: {}
Субъект: {}
Район: {}
Население: {}
Высота НУМ: {}
Временная зона: {}
Данные по состоянию на {}\n""".format(line[1], line[2], line[3], line[4], line[5],
line[6], line[7], line[8], line[9], line[10]).encode())
                except IndexError:
                    client.send('\nНесуществующая страница или недопустимое количество населённых пунктов.\n'.encode())

            # Обработка третьего метода
            elif '3' == request:
                errors = True
                while errors:
                    try:
                        client.send('\nВведите название первого населённого пункта с соблюдением регистра: '.encode())
                        name_1 = client.recv(64).decode().rstrip('\n')
                        client.send('\nВведите название второго населённого пункта с соблюдением регистра: '.encode())
                        name_2 = client.recv(64).decode().rstrip('\n')
                        names = (name_1, name_2)
                        approved_names = []
                        for name in names:
                            name = (name,)
                            check = cur.execute("SELECT name, population FROM places WHERE name = ?;", name)
                            checked_name = check.fetchall()
                            if checked_name is None:
                                raise ValueError
                            else:
                                population = []
                                for line in checked_name:
                                    line = list(line)
                                    line[1] = int(line[1])
                                    population.append(line[1])
                                highest_pop = max(population)
                                found_place = (checked_name[0][0], str(highest_pop))
                                cur.execute("SELECT name, population FROM places WHERE name = ? AND population = ?;", found_place)
                                approved_name = list(cur.fetchone())
                                approved_names.append(approved_name)
                    except ValueError:
                        client.send('\nОшибка ввода или населённого(-ых) пункта(-ов) не существует.\n'.encode())
                    else:
                        errors = False
                try:
                    assert approved_names[0][0] != approved_names[1][0]
                except AssertionError:
                    client.send('\nВы выбрали один и тот же населённый пункт!\n'.encode())
                else:
                    for name in approved_names:
                        cur.execute("SELECT latitude FROM places WHERE name = ? AND population = ?;", name)
                        latitude = cur.fetchone()[0]
                        name.append(float(latitude))
                    if approved_names[0][2] > approved_names[1][2]:
                        compared = '{} севернее, чем {}.'.format(approved_names[0][0], approved_names[1][0])
                    elif approved_names[0][2] < approved_names[1][2]:
                        compared = '{} севернее, чем {}.'.format(approved_names[1][0], approved_names[0][0])
                    else:
                        compared = 'Населённые пункты с заданной точностью расположены на одной широте.'
                    for name in approved_names:
                        name.pop()
                        cur.execute("SELECT timezone FROM places WHERE name = ? AND population = ?;", name)
                        timezone = int(cur.fetchone()[0])
                        name.append(timezone)
                    difference = str(abs(approved_names[0][2] - approved_names[1][2]))
                    if approved_names[0][2] != approved_names[1][2]:
                        tz = 'Населённые пункты расположены в разных временных зонах. Разница во времени - {} час(-ов/-а).'.format(difference)
                    else:
                        tz = 'Населённые пункты расположены в одной временной зоне.'
                    client.send('\nРезультат поиска:\n'.encode())
                    for name in approved_names:
                        name.pop()
                        cur.execute("SELECT * FROM places WHERE name = ? AND population = ?;", name)
                        line = list(cur.fetchone())
                        line = null_replacement(line)
                        line[-2] = timezone_correction(line[-2])
                        client.send("""
Населённый пункт: {}
Другие названия: {}
Широта: {}
Долгота: {}
Субъект: {}
Район: {}
Население: {}
Высота НУМ: {}
Временная зона: {}
Данные по состоянию на {}\n""".format(line[1], line[2], line[3], line[4], line[5],
line[6], line[7], line[8], line[9], line[10]).encode())
                    client.send('\n{}\n{}\n'.format(compared, tz).encode())

            # Обработка четвёртого метода
            elif '4' == request:
                client.send('\nВведите часть названия населённого пункта с соблюдением регистра: '.encode())
                substring = client.recv(64).decode().rstrip('\n')
                cur.execute("SELECT DISTINCT name FROM places;")
                name_set = cur.fetchall()
                results = []
                for name in name_set:
                    name = name[0]
                    if substring in name:
                        results.append(name)
                client.send('\nРезультат поиска:\n'.encode())
                for name in results:
                    client.send('{}\n'.format(name).encode())

            # Отключение от сервера
            elif 'q' == request:
                break

            else:
                client.send('\nОшибка ввода! Повторите попытку.\n'.encode())

        client.close()
