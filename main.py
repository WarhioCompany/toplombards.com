import json
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import codecs
import time
import xlsxwriter
from os.path import exists
import os

from bs4 import BeautifulSoup

from geopy import distance

import find_urls_for_yandex_maps as find_urls

def get_distance(first_point, second_point):
    return distance.distance(first_point, second_point).meters


def passed_threshold(first_point, second_point):
    return get_distance(first_point, second_point) < 100


start_url = 'https://yandex.com/maps/1/moscow-and-moscow-oblast/category/pawnshop'#'https://yandex.kz/maps/213/moscow/search/%D0%9B%D0%BE%D0%BC%D0%B1%D0%B0%D1%80%D0%B4/' #'https://yandex.ru/maps/213/moscow/category/pawnshop'
max_resless_in_a_row = 5

def get_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    return chrome_options


def start_driver(url):
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=get_options())
    driver = set_driver(driver)
    driver.get(url)

    return driver


def set_driver(driver):
    driver.implicitly_wait(3)
    return driver


def shallow_parse(url, driver=None):
    if not driver:
        driver = start_driver(url)

    elements_html = scroll_all_elements(driver)

    elements = shallow_parse_elements(elements_html)

    return remove_duplicates(elements)


def remove_duplicates(arr):
    res = []
    [res.append(x) for x in arr if x not in res]
    return res


def find_element_by_class(driver, element_type, class_name):
    return WebDriverWait(driver, 10).until(
        #EC.presence_of_element_located((By.XPATH, f"//{element_type}[contains(@class, '{class_name}')]"))
        EC.presence_of_element_located((By.XPATH, find_by_class_short(element_type, class_name)))
    )


def parse_pages(elements, id = 0, resless_count=0):
    j = []

    not_parsed = []

    driver = start_driver(start_url)
    i = 0
    for element in elements:
        print(f"({i}/{len(elements)}) {element['link']} (errors: {len(not_parsed)})")
        driver = set_driver(driver)
        driver.get(element['link'])

        try:
            res = deep_parse(driver)

            res['name'] = element['name']
            res['link'] = element['link']
            res['rating'] = element['rating']

            j.append(res)

            i += 1
        except Exception:
            traceback.print_exc()
            not_parsed.append(element)

    print('saving data..')
    if j:
        save(os.path.join('temp_res',f'res{id}.json'), json.dumps(j, ensure_ascii=False))
        resless_count = 0
    else:
        resless_count += 1

    if not_parsed and resless_count <= max_resless_in_a_row:
        j += parse_pages(not_parsed, id+1, resless_count)

    return j


def save(file_name, data):
    print('writing to a file')
    mode = 'w'
    if not exists(file_name):
        mode = 'x'
    with codecs.open(file_name, mode, 'utf-8') as f:
        f.write(data)


def scroll_all_elements(driver):

    def get_element_to_scroll_to(driver, elements):
        try:
            # last_element = driver.find_element(By.XPATH, "//ul[contains(@class, 'search-list-view__list')]/div[last()]")
            last_element = find_element_by_class(driver, 'ul', 'search-list-view__list').find_element(By.XPATH, 'div[last()]')
        except:
            try:
                last_element = elements[-1]
            except:
                print(driver.find_element(By.XPATH, "//ul[contains(@class, 'search-list-view__list')]").
                      get_attribute("outerHTML"))
                return None
        return last_element

    def try_scroll(element):
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
        except:
            pass

    arr_max_size = 10
    iterations_res = [i for i in range(arr_max_size)]

    i = 0

    elements_count = -1

    while iterations_res[0] != elements_count:
        elements = driver.find_elements(By.XPATH, "//ul[contains(@class, 'search-list-view__list')]/li")

        elements_count = len(elements)

        iterations_res.append(elements_count)
        iterations_res.pop(0)

        try_scroll(get_element_to_scroll_to(driver, elements))

        time.sleep(.5)

    print(f"Places found {elements_count}")
    return elements


def shallow_parse_elements(elements_html):

    def parse_rating(element_html):
        try:
            rating = element_html.find_element(By.XPATH, "div/div/div/div/div[5]/div[1]/div/span/span/span[2]").text
        except:
            rating = '-'
        return rating

    elements = []
    for element_html in elements_html:
        try:
            link_and_name = element_html.find_element(By.CSS_SELECTOR, 'div.search-snippet-view__body._type_business > div > a')
        except:
            print('Skipping element')
            continue
        link = link_and_name.get_attribute("href")
        name = link_and_name.text
        rating = parse_rating(element_html)
            #address = element_html.find_element(By.CSS_SELECTOR, "div.search-business-snippet-view__address").text

        element = {
            "link": link,
            "name": name,
            "rating": rating,
        }
        elements.append(element)
        print(element)

    return elements


def deep_parse(element_page):
    #address_element = element_page.find_element(By.XPATH, "//a[contains(@class, 'business-contacts-view__address-link')]")


    #schedule = parse_schedule(element_page)

    phones = parse_phones(element_page)

    websites = parse_websites(element_page)

    #photos = parse_photos(element_page)

    address_element = find_element_by_class(element_page, 'a', 'business-contacts-view__address-link')
    address = address_element.text
    coordinates, pivot_name, pivot_distance = get_coordinates(address_element.get_attribute("href"), element_page)

    return {
        "address": address,
        "coordinates": coordinates.split(', '),
        "pivot_point_name": pivot_name,
        "pivot_point_distance": pivot_distance,
        "phones": phones,
        "websites": websites,
        #"photos": photos,
        #"schedule": schedule
    }


def parse_schedule(element_page):
    # element_page.find_element(By.XPATH, "//div[contains(@class, 'business-card-working-status-view__text')]").click()
    find_element_by_class(element_page, 'div', 'business-card-working-status-view__text').click()

    schedule_html = element_page.find_elements(By.XPATH, "//div[contains(@class, 'business-working-intervals-view__interval')]")
    schedule = list(map(lambda x: x.text, schedule_html))
    return schedule


def parse_phones(element_page):
    phone = try_find(element_page, find_by_class_short('div', 'card-phones-view__number'))
    if not phone:
        print('no phones')
        return []
    else:
        phones = [phone.text.split('\n')[0]]
    try:
        '/div/div/div[1]/div[1]/div[2]'
        find_element_by_class(element_page, 'div', 'card-phones-view__more').click()

        parent = find_element_by_class(element_page, 'div', 'card-phones-view')
        #find_element_by_class(parent, 'div', 'card-feature-view__additional').click()
        arrow = try_find(parent, 'div/div/div[1]/div[1]/div[2]')
        if not arrow:
            print(phones)
            return phones
        else:
            arrow.click()
            phones_html = element_page.find_elements(By.XPATH, "//div[contains(@class, 'card-phones-view__phone-number')]")
            #phones_html = find_element_by_class(element_page, 'div', 'card-phones-view__phone-number')
            phones = []
            for phone_html in phones_html:
                if phone_html.text != '':
                    phones.append(phone_html.text)
    except Exception:
        traceback.print_exc()
    print(phones)
    return phones


def parse_websites(element_page):
    website = try_find(element_page, find_by_class_short('span', 'business-urls-view__text'))
    if not website:
        website = find_bs4(element_page.page_source, 'span', 'business-urls-view__text')

    if not website:
        save('debug.html', element_page.page_source)
        print('no websites')
        return []

    websites_container = try_find(element_page, find_by_class_short('div', 'business-urls-view _wide'))
    print(website.text)


    # BUG it's changing it's url
    #more_websites_button = try_find(websites_container, find_by_class_short('div', 'card-feature-view__additional'))
    #if not more_websites_button:
    #    print('only one website')
    #    return [website.text]
    #else:
    #    more_websites_button.click()
    #    all_websites_html = find_all_bs4(element_page.page_source, 'span', 'business-urls-view__text')#try_find_all(websites_container, find_by_class_short('span', 'card-feature-view__additional'), crucial=True)
    #    print(f'{len(all_websites_html)} websites')
    #    return [x.text for x in all_websites_html]

    return [website.text]

def try_find(driver, xpath, crucial=False):
    try:
        return driver.find_element(By.XPATH, xpath)
    except:
        cant_find_xpath_log(xpath, crucial)


def try_find_all(driver, xpath, crucial=False):
    try:
        return driver.find_elements(By.XPATH, xpath)
    except:
        cant_find_xpath_log(xpath, crucial)


def find_bs4(source_code, elem_type, class_name):
    soup = BeautifulSoup(source_code, 'html.parser')
    return soup.find(elem_type, class_=class_name)


def find_all_bs4(source_code, elem_type, class_name):
    soup = BeautifulSoup(source_code, 'html.parser')
    return soup.find_all(elem_type, class_=class_name)


def find_by_class_short(elem_type, class_name):
    return f"//{elem_type}[contains(@class, '{class_name}')]"


def cant_find_xpath_log(xpath, crucial):
    if not crucial:
        print(f'ERROR cant find element(s) by this xpath:\n\t{xpath}')
    else:
        raise Exception(f'ERROR cant find element(s) by this xpath:\n\t{xpath}')


def parse_photos(element_page):
    find_element_by_class(element_page, 'div', 'tabs-select-view__title _name_gallery').click()

    photos = []

    photos_html = element_page.find_elements(By.XPATH, "//img[contains(@class, 'photo-wrapper__photo')]")
    for photo_html in photos_html:
        photos.append(photo_html.get_attribute('src'))
    return photos


def parse_reviews(element_page):
    find_element_by_class(element_page, 'div', 'tabs-select-view__title _name_reviews _selected').click()

    return []


def get_coordinates(address_link, driver):
    try:
        print(address_link)
        driver.get(address_link)
        driver = set_driver(driver)

        coordinates = find_element_by_class(driver, 'div', 'toponym-card-title-view__coords-badge').text
    except:
        print('wtf')
        save('debug.html', driver.page_source)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        coordinates = soup.find("div", {"class": "toponym-card-title-view__coords-badge"}).text
        print(coordinates)


    try:
        pivot_point = find_element_by_class(driver, 'div', 'masstransit-stops-view__stop _type_metro')
        pivot_point_name = pivot_point.find_element(By.XPATH, "div").text
        pivot_point_distance = pivot_point.find_element(By.XPATH, "div[2]/div[2]").text
    except:
        print('no metro')
        pivot_point_name = '-'
        pivot_point_distance = '-'
    return coordinates, pivot_point_name, pivot_point_distance


def file_to_object(file_name):
    with codecs.open(file_name, 'r', 'utf-8-sig') as f:
        return json.loads(f.read())


def object_to_file(file_name, data):
    save(file_name, json.dumps(data, ensure_ascii=False))


def merge_files(first_file, second_file, final_file_name):
    first_file_data = file_to_object(first_file)
    print(f'first file len: {len(first_file_data)}')
    second_file_data = file_to_object(second_file)
    print(f'Second file len: {len(second_file_data)}')
    final_data = merge_arrays([first_file_data, second_file_data])
    print(f'Final file len: {len(final_data)}')
    object_to_file(final_file_name, final_data)


def merge_arrays(arrays):
    res = []
    for arr in arrays:
        [res.append(x) for x in arr if x not in res]
    return res


def to_xlsx(arr, name):
    workbook = xlsxwriter.Workbook(f'{name}.xlsx')
    worksheet = workbook.add_worksheet()

    bold = workbook.add_format({'bold': True})

    worksheet.write(0, 0, 'Имя', bold)
    worksheet.write(0, 1, 'Адрес', bold)
    worksheet.write(0, 2, 'Рейтинг', bold)
    worksheet.write(0, 3, 'Контакты', bold)
    worksheet.write(0, 4, 'Вебсайты', bold)
    worksheet.write(0, 5, 'Координаты', bold)
    worksheet.write(0, 6, 'Ближайшее метро', bold)
    worksheet.write(0, 7, 'Есть в официальном файле')

    for i in range(len(arr)):
        worksheet.write(i + 1, 0, arr[i]['name'])
        worksheet.write(i + 1, 1, arr[i]['address'])
        worksheet.write(i + 1, 2, arr[i]['rating'])
        worksheet.write(i + 1, 3, ', '.join(arr[i]['phones']))
        worksheet.write(i + 1, 4, ', '.join(arr[i]['websites']))
        worksheet.write(i + 1, 5, ', '.join(arr[i]['coordinates']))
        worksheet.write(i + 1, 6, f"{arr[i]['pivot_point_name']}, {arr[i]['pivot_point_distance']}")
        try:
            if arr[i]['official']:
                worksheet.write(i + 1, 7, "Да")
            else:
                worksheet.write(i + 1, 7, "Нет")
        except:
            worksheet.write(i + 1, 7, "?")

    workbook.close()


def parse(search_link, file_name):
    try:
        shallow = shallow_parse(search_link)
    except:
        try:
            print(f'ERROR OCCURRED (shallow parse): {search_link}\n\ttrying to resolve')
            traceback.print_exc()
            driver = start_driver(search_link)

            print(driver.current_url)

            elem = find_element_by_class(driver, 'div', 'small-search-form-view__icon _type_back')
            elem.click()

            print(driver.current_url)

            shallow = shallow_parse(driver.current_url, driver)
            print(shallow)
            print('SUCCESSFUL')
        except:
            print("No elements")
            shallow = []
    object_to_file(os.path.join('shallow_res', f'{file_name}_shallow.json'), shallow)

    res = parse_pages(shallow)
    object_to_file(os.path.join('res', f'{file_name}.json'), res)

    return res


def parse_urls(urls, final_file_name, add_to_url):
    results = []
    i = 1
    for url in urls:
        print(f'{i}/{len(urls)}: {url}')
        name = url.split('/')[-1].replace('\n', '')
        results = merge_arrays([results, parse(f'{url}{add_to_url}', name)])
        i += 1
    object_to_file(final_file_name, results)
    return results

if not os.path.isdir('temp_res'):
    os.makedirs('temp_res')
if not os.path.isdir('res'):
    os.makedirs('res')
if not os.path.isdir('shallow_res'):
    os.makedirs('shallow_res')

with open('urls.txt', 'r') as f:
    res = parse_urls(f.readlines(), 'final.json', '/search/скупка%20золото')
    to_xlsx(res, 'final')
