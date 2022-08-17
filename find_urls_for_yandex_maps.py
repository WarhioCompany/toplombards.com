import time

from selenium import webdriver
import codecs

from os.path import exists

from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

import json

def get_names():
    names = []
    driver = webdriver.Chrome(ChromeDriverManager().install())

    url = 'https://ru.wikipedia.org/wiki/%D0%93%D0%BE%D1%80%D0%BE%D0%B4%D1%81%D0%BA%D0%B8%D0%B5_%D0%BD%D0%B0%D1%81%D0%B5%D0%BB%D1%91%D0%BD%D0%BD%D1%8B%D0%B5_%D0%BF%D1%83%D0%BD%D0%BA%D1%82%D1%8B_%D0%9C%D0%BE%D1%81%D0%BA%D0%BE%D0%B2%D1%81%D0%BA%D0%BE%D0%B9_%D0%BE%D0%B1%D0%BB%D0%B0%D1%81%D1%82%D0%B8'
    driver.get(url)

    table_elements = driver.find_elements(By.XPATH, '//table[2]/tbody/tr')
    for table_element in table_elements:
        names.append(table_element.find_element(By.XPATH, 'td[2]').text)

    return names



def get_names_from_file():
    with codecs.open('names.txt', 'r', 'utf-8') as f:
        return f.readlines()


def get_url(name):
    return f'https://www.google.com/search?q=%D1%8F%D0%BD%D0%B4%D0%B5%D0%BA%D1%81+%D0%BA%D0%B0%D1%80%D1%82%D1%8B+{name}+%D1%81%D0%BF%D1%83%D1%82%D0%BD%D0%B8%D0%BA'


def clean_urls():
    with open('urls.txt', 'r') as f:
        lines = []
        for line in f:
            url = '/'.join(line.split('/')[:-2])
            lines.append(url)
        with codecs.open('urls_new.txt', 'x', 'utf-8') as new_file:
            for line in lines:
                new_file.write(f'{line}\n')


def get_urls_google():
    urls = []
    names = get_names_from_file()
    driver = webdriver.Chrome(ChromeDriverManager().install())
    for name in names:
        driver.get(get_url(name))
        url = driver.find_element(By.XPATH, f"//div[contains(@class, 'yuRUbf')]/a").get_attribute('href')
        urls.append(url)
        print(f'{name}: {url}')
        time.sleep(2)
    return urls

def save(file_name, data):
    print('writing to a file')
    mode = 'w'
    if not exists(file_name):
        mode = 'x'
    with codecs.open(file_name, mode, 'utf-8') as f:
        f.write(data)


urls = get_urls_google()
mode = 'w'
if not exists('urls.txt'):
    mode = 'x'
with open('urls.txt', mode) as f:
    for url in urls:
        url = '/'.join(url.split('/')[:-2])
        f.write(f'{url}\n')

