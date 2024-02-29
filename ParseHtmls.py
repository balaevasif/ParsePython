from bs4 import BeautifulSoup
from pathlib import Path
from collections import defaultdict
import os
import csv
import json
import zipfile


# разбил парсинг на мелкие части для удобства

def parse_title(header):
    title_tag = header.find('a')
    return title_tag.text.strip() if title_tag else None


def parse_year(header):
    year_tag = header.find('span', class_='lister-item-year')
    return year_tag.text.strip('()') if year_tag else None


# прибыль и голоса
def parse_gross_and_votes(info_tag):
    gross_value = None
    votes = None
    if info_tag:
        gross_span = info_tag.find('span', string='Gross:')
        if gross_span:
            gross_value_span = gross_span.find_next('span', attrs={"name": "nv"})
            gross_value = gross_value_span.text.strip() if gross_value_span else None

        votes_span = info_tag.find('span', string='Votes:')
        if votes_span:
            votes_value_span = votes_span.find_next('span', attrs={"name": "nv"})
            votes = int(votes_value_span['data-value'].replace(',', '')) if votes_value_span else None
    return gross_value, votes


#возрастной ценз, продолжительность и жанр
def parse_certificate_runtime_genre(details_tag):
    certificate = None
    runtime = None
    genre = None
    if details_tag:
        certificate_span = details_tag.find('span', class_='certificate')
        certificate = certificate_span.text.strip() if certificate_span else None

        runtime_span = details_tag.find('span', class_='runtime')
        runtime = runtime_span.text.strip() if runtime_span else None

        genre_span = details_tag.find('span', class_='genre')
        genre = genre_span.text.strip() if genre_span else None
    return certificate, runtime, genre


#режиссёр и актёры
def parse_director_and_stars(cast_info_tag):
    director = None
    stars = []
    if cast_info_tag:
        director_tag = cast_info_tag.find('a')
        director = director_tag.text.strip() if director_tag else None

        stars_tags = cast_info_tag.find_all('a')[1:]  # срезаем первого
        stars = [star_tag.text.strip() for star_tag in stars_tags]
    return director, stars


#рейтинги на imdb и metascore
def parse_imdb_rating_and_metascore(ratings_bar):
    imdb_rating = None
    metascore = None
    if ratings_bar:
        imdb_rating_tag = ratings_bar.find('div', class_='ratings-imdb-rating')
        imdb_rating = imdb_rating_tag.get('data-value', None) if imdb_rating_tag else None

        metascore_tag = ratings_bar.find('span', class_='metascore')
        metascore = metascore_tag.text.strip() if metascore_tag else None
    return imdb_rating, metascore


def parse_movie_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    movie_headers = soup.find_all('h3', class_='lister-item-header')
    movies_list = []

    for header in movie_headers:
        title = parse_title(header)
        year = parse_year(header)
        info_tag = header.find_next_sibling('p', class_='sort-num_votes-visible')
        gross, votes = parse_gross_and_votes(info_tag)
        details_tag = header.find_next_sibling('p', class_='text-muted')
        certificate, runtime, genre = parse_certificate_runtime_genre(details_tag)
        cast_info_tag = header.find_next_sibling('p', class_='')
        director, stars = parse_director_and_stars(cast_info_tag)
        ratings_bar = header.find_next_sibling('div', class_='ratings-bar')
        imdb_rating, metascore = parse_imdb_rating_and_metascore(ratings_bar)

        if title:
            movies_list.append({
                'title': title, 'year': year, 'gross': gross, 'votes': votes,
                'certificate': certificate, 'runtime': runtime, 'genre': genre,
                'director': director, 'stars': stars,
                'imdb_rating': imdb_rating, 'metascore': metascore
            })

    return movies_list


# путь до зипа и для распаковки
zip_file_path = 'movies_html.zip'
extraction_directory = 'movies_html'

Path(extraction_directory).mkdir(exist_ok=True)

with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
    zip_ref.extractall(extraction_directory)

directory_path = extraction_directory

all_movies_data = {}

# побежали по всем html'кам
for root, dirs, files in os.walk(directory_path):
    for file_name in files:
        if file_name.endswith('.html'):
            file_path = os.path.join(root, file_name)
            movies_data = parse_movie_data(file_path)
            for movie in movies_data:  # из кортежа в словарь
                # Сохраните уникальные наблюдения по названию фильма и году.
                all_movies_data[(movie['title'], movie['year'])] = movie

# Конвертнем словарь в лист для датасета
unique_movies_dataset = list(all_movies_data.values())

# Пример датасета
for movie in unique_movies_dataset[:5]:
    print(movie)

print("_____________")


# 2.2. Найдите фильм с наибольшим доходом (revenue), если таких фильмов несколько, выведите их все. Наверное всё же gross, а не revenue
def parse_gross(gross_str):
    if gross_str is None:
        return 0
    return float(gross_str.replace('$', '').replace('M', '').replace(',', ''))


highest_gross = 0
highest_gross_movies = []

for movie in unique_movies_dataset:
    movie_gross = parse_gross(movie['gross'])
    if movie_gross > highest_gross:
        highest_gross = movie_gross
        highest_gross_movies = [movie]
    elif movie_gross == highest_gross:
        highest_gross_movies.append(movie)

for movie in highest_gross_movies:
    print(movie)

# 2.3. Найдите актера, который чаще всего появляется в этом наборе данных, если таких актеров несколько, выведите их всех.
actor_count = defaultdict(int)

for movie in unique_movies_dataset:
    for actor in movie['stars']:
        actor_count[actor] += 1

max_appearances = max(actor_count.values())

most_frequent_actors = [actor for actor, count in actor_count.items() if count == max_appearances]

print("Чаще всего встречающийся актёр(ы):")
for actor in most_frequent_actors:
    print(actor)

# 2.4. Найти пару режиссер-актер (в одном фильме), которая чаще всего появляется в этом наборе данных, если таких пар несколько, выведите их все.
director_actor_count = defaultdict(int)

for movie in unique_movies_dataset:
    director = movie['director']
    for actor in movie['stars']:
        # У меня получалось самая частая пара - Вуди Аллен и Вуди Аллен, поэтому решил убрать такой вариант, неинтересно
        # Если всё же нужно как по ТЗ, то просто закомментировать следующие 3 строки и раскомментировать 2 идущие за ними
        if director != actor:
            director_actor_pair = (director, actor)
            director_actor_count[director_actor_pair] += 1
        # director_actor_pair = (director, actor)
        # director_actor_count[director_actor_pair] += 1

# Максимальное количество появлений для пары
max_pair_appearances = max(director_actor_count.values())

# Найти все пары с максимальным количеством появлений
most_frequent_pairs = [pair for pair, count in director_actor_count.items() if count == max_pair_appearances]

print("Самая частая пара:")
for director, actor in most_frequent_pairs:
    print(f"Режиссёр: {director}, актёр: {actor}")

# Запишем для удобства в Json и CSV наш датасет
output_csv_file = 'movies_dataset.csv'
output_json_file = 'movies_dataset.json'

fieldnames = list(unique_movies_dataset[0].keys())

with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for movie in unique_movies_dataset:
        movie['stars'] = ', '.join(movie['stars'])
        writer.writerow(movie)

print(f"Csv сохранён {output_csv_file}")

with open(output_json_file, 'w', encoding='utf-8') as jsonfile:
    json.dump(unique_movies_dataset, jsonfile, ensure_ascii=False, indent=4)

print(f"Json сохранён {output_json_file}")
