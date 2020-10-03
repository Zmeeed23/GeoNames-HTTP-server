# GeoNames based HTTP server
Проект реализует часть функционала сервиса [GeoNames](https://www.geonames.org/) на localhost'е. Исполняющий код находится в файле [script.py](./script.py). Для работы скрипта необходимо наличие подключения к Интернету.
---
### Описание программы
[Скрипт](./script.py) запускается из консоли в корневом каталоге командой: `$ python3 script.py`. После запуска скрипт создаёт таблицу в резидентной базе данных средствами библиотеки *sqlite3* и открывает для чтения файл [RU.txt](./RU.txt) с необработанными данными, взятыми из сервиса [GeoNames](https://www.geonames.org/).
Таблица содержит следующие поля:

1. Уникальный числовой идентификатор;
2. Название населённого пункта;
3. Другие названия населённого пункта;
4. Географическая широта;
5. Географическая долгота;
6. Субъект, в состав которого входит населённый пункт;
7. Район или округ, в состав которого входит населённый пункт;
8. Численность населения;
9. Высота над уровнем моря (НУМ);
10. Временная зона относительно московского времени;
11. Дата, на которую приведены данные о населённом пункте.

Обработка данных производится методами библиотеки *re*. После обработки данные записываются в поля таблицы.

Следующая часть кода производит редактирование данных в таблице, переводя названия населённых пунктов с транслита на русский язык, заменяя числовые коды субъектов и районов на их названия и изменяя поля временной зоны для удобства работы с ними. При редактировании полей числовых кодов районов и временной зоны происходит запрос текстовых данных с сервера [GeoNames](https://www.geonames.org/) методом **get()** библиотеки *requests*, для чего и необходимо наличие подключения к Интернету.

После редактирования всех полей происходит инициализация серверного сокета по адресу `127.0.0.1:8000` средствами библиотеки *socket*. После подключения к серверу становятся доступными 4 метода работы с данными, хранящимися в таблице. Для завершения [скрипта](./script.py) необходимо использовать сочетание клавиш ***Ctrl+C***. Для отключения от сервера необходимо нажать клавишу ***q*** на клавиатуре.

### Описание методов
##### Метод 1
Метод принимает числовой идентификатор искомого населённого пункта, после чего производит поиск записи с заданным идентификатором и вывод её информации пользователю.

```python
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
```

##### Метод 2
Метод принимает количество населённых пунктов, которые будут отображены на странице, и номер страницы, которую необходимо отобразить пользователю. Все записи в таблице отсортированы по возрастанию значения числового идентификатора.

```python
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
```

##### Метод 3
Метод принимает названия двух населённых пунктов, информацию о которых необходимо отобразить, а также выводит сравнительную информацию: находятся ли населённые пункты в одинаковых временных зонах или в разных, и если в разных, то выводится информация о разнице во времени; и указывается, какой из населённых пунктов расположен севернее.

Если по заданному названию в таблице есть несколько записей, то выводится информация о той, население которой наибольшее. Если есть записи с одинаковыми названиями и одинаковым населением, то выводится информация о той, значение числового идентификатора которой меньше.

```python
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
```

##### Метод 4
Метод принимает часть названия населённого пункта (подстроку) и производит поиск по таблице на наличие вхождений подстроки в название какого-либо населённого пункта, после чего отображает пользователю все названия с заданной подстрокой.

```python
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
```
