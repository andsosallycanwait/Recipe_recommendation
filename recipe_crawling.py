import pandas as pd
import re
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

"""데이터 전처리 함수 정의"""
def is_whitespace(char):
    return char.isspace() or char == '\n' or char == '\r' or char == '\t'

def extract_words(s):
    # 알파벳과 숫자만 포함하는 단어들을 찾아 리스트로 반환
    words = re.findall(r'\b\w+\b', s)
    return words


# CSV 파일 불러오기
data = pd.read_csv("datas/RAW_recipes.csv")
data = data.dropna(subset=['name'])

"""query string 만들기"""
recipe_name = []
recipe_id = []
for name in data['name']:
    recipe_name.append(name)
for id in data['id']:
    recipe_id.append(id)

char = []
for name in data['name']:
    for c in name:
        if not is_whitespace(c):
            char.append(c)
            
query_strs = []
for index in range(len(recipe_name)):
    name = recipe_name[index]
    id = recipe_id[index]
    
    name_words = extract_words(name)
    
    query_str = ""
    for word in name_words:
        query_str += word
        query_str += "-"
    query_str += str(id)
    
    query_strs.append(query_str)

recipe_list = []
for index in range(len(recipe_name)):
    recipe_info = (recipe_name[index], recipe_id[index], query_strs[index], "https://www.food.com/recipe/" + query_strs[index])
    recipe_list.append(recipe_info)
    
"""데이터 추출에 필요한 함수 정의"""
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run without opening a browser window
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_text_with_spaces(element):
    """
    태그의 내용물을 순회하며 텍스트와 <a> 태그의 텍스트 사이에 공백을 삽입합니다.
    """
    texts = []
    for content in element.contents:
        if content.name == 'a':
            texts.append(content.get_text(strip=True))
        elif content.string:
            texts.append(content.string.strip())
    return ' '.join(text for text in texts if text)

def get_ingredients(query_str):
    soup = get_webpage(query_str)
                
    # Now find the ingredients and quantities
    ingredients_section = soup.find("section", class_="layout__item ingredients svelte-1dqq0pw")
    ingredients = []
    if ingredients_section:
        li_elements = ingredients_section.find_all("li", style="display: contents")
        for li in li_elements:
            get_text_with_spaces(li)
            # Check if 'ingredient-heading' is not in li
            if not li.find("h4", class_="ingredient-heading"):
                quantity_span = li.find("span", class_="ingredient-quantity svelte-1dqq0pw")
                text_span = li.find("span", class_="ingredient-text svelte-1dqq0pw")
                
                quantity = quantity_span.get_text(strip=True) if quantity_span else ""
                ingredient_text = get_text_with_spaces(text_span) if text_span else ""
                
                ingredients.append((quantity, ingredient_text))
    return ingredients

def get_webpage(query_str):
    
    driver = setup_driver()
    driver.get("https://www.food.com/recipe/" + query_str)
    
    # Wait for the page and JavaScript to load
    time.sleep(2)
    
    # Click the button by XPath
    try:
        search_button = driver.find_element(By.XPATH, '//*[@id="recipe"]/section[1]/div[1]/button')
        search_button.click()
        time.sleep(2)  # Wait for any dynamic content to load
    except Exception as e:
        print(f"Error clicking button: {str(e)}")
    
    # Process the new page content
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    return soup

def to_dict(ingredients):
    recipe_ingredients = {}
    
    for quant, ing in ingredients:
        if quant == "":
            quant = str(0.0)
        recipe_ingredients[ing] = quant

    return recipe_ingredients

def save_to_csv(df, new_data):
    new_data = pd.DataFrame(new_data)
    pd.concat([df, pd.DataFrame(new_data)], axis = 0)
    
"""크롤링"""
foodcom_data = pd.DataFrame(columns = ['Name', 'Id', 'Ingredients', 'URL'])

index = 1
for name, id, query_str, url in recipe_list:
    ingredients = to_dict(get_ingredients(query_str))
    
    print(f"====== {index} : Complete crawling ingredients of {name} ======")
    
    new_row = pd.DataFrame([{'Name' : name, 'Id' : id, 'Ingredients':ingredients, 'URL':url}])
    foodcom_data = pd.concat([foodcom_data, pd.DataFrame(new_row)], axis = 0)
    
    foodcom_data.to_csv("datas/recipe_ingredients.csv", mode='w')
    
    time.sleep(random.randint(1, 31))
    index+=1