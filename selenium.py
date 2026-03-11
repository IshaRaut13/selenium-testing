import os
import re
import json
import requests
from collections import Counter

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator


BASE_URL = "https://elpais.com/opinion/"
os.makedirs("images", exist_ok=True)


# ---------------------------------------------------
# DRIVER SETUP
# ---------------------------------------------------
def create_driver():

    chrome_options = Options()

    chrome_options.add_argument("--lang=es")
    chrome_options.add_argument("--start-maximized")

    # 🔥 Uncomment for faster execution
    # chrome_options.add_argument("--headless=new")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    return driver


# ---------------------------------------------------
# DOWNLOAD IMAGE
# ---------------------------------------------------
def download_image(url, index):

    try:
        img = requests.get(url, timeout=15)

        with open(f"images/article_{index}.jpg", "wb") as f:
            f.write(img.content)

    except Exception as e:
        print("Image download failed:", e)


# ---------------------------------------------------
# CLEAN WORDS
# ---------------------------------------------------
def clean_words(text):
    return re.findall(r"[A-Za-z]+", text.lower())


# ---------------------------------------------------
# SCRAPE ARTICLES (FIXED VERSION)
# ---------------------------------------------------
def scrape_articles(driver):

    wait = WebDriverWait(driver, 20)

    driver.get(BASE_URL)

    # Accept cookies if shown
    try:
        wait.until(
            EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
        ).click()
    except:
        pass

    # Grab headline links instead of generic <article>
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2 a")))

    soup = BeautifulSoup(driver.page_source, "html.parser")

    headline_links = soup.select("h2 a")[:5]

    links = []

    for tag in headline_links:
        link = tag.get("href")

        if link and not link.startswith("http"):
            link = "https://elpais.com" + link

        links.append(link)

    articles_data = []

    for idx, link in enumerate(links, start=1):

        driver.get(link)

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        article_soup = BeautifulSoup(driver.page_source, "html.parser")

        # Title
        title_tag = article_soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "No title"

        # Content (filtered)
        paragraphs = article_soup.select("article p")

        content = "\n".join(
            p.get_text(strip=True)
            for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        )

        # Cover image (reliable)
        meta_img = article_soup.find("meta", property="og:image")

        if meta_img:
            download_image(meta_img["content"], idx)

        articles_data.append({"title_es": title, "content_es": content, "url": link})

    return articles_data


# ---------------------------------------------------
# TRANSLATE
# ---------------------------------------------------
def translate_titles(articles):

    translator = GoogleTranslator(source="auto", target="en")

    translated_titles = []

    for art in articles:
        translated = translator.translate(art["title_es"])
        art["title_en"] = translated
        translated_titles.append(translated)

    return translated_titles


# ---------------------------------------------------
# SAVE FILES
# ---------------------------------------------------
def save_spanish_articles(articles):

    with open("spanish_articles.txt", "w", encoding="utf-8") as f:

        for i, art in enumerate(articles, 1):

            f.write(f"\n{'='*80}\n")
            f.write(f"ARTICLE {i}\n")
            f.write(f"{'='*80}\n\n")

            f.write("TITLE:\n")
            f.write(art["title_es"] + "\n\n")

            f.write("URL:\n")
            f.write(art["url"] + "\n\n")

            f.write("CONTENT:\n")
            f.write(art["content_es"] + "\n\n")


def save_translated_articles(articles):

    with open("translated_articles.txt", "w", encoding="utf-8") as f:

        for i, art in enumerate(articles, 1):

            f.write(f"\n{'='*80}\n")
            f.write(f"ARTICLE {i}\n")
            f.write(f"{'='*80}\n\n")

            f.write("SPANISH TITLE:\n")
            f.write(art["title_es"] + "\n\n")

            f.write("ENGLISH TITLE:\n")
            f.write(art["title_en"] + "\n\n")

            f.write("URL:\n")
            f.write(art["url"] + "\n\n")


def save_json(articles):

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)


# ---------------------------------------------------
# WORD ANALYSIS
# ---------------------------------------------------
def analyze_words(titles):

    words = []

    for t in titles:
        words.extend(clean_words(t))

    counter = Counter(words)

    print("\n====== REPEATED WORDS (>2) ======\n")

    found = False

    for word, count in counter.items():
        if count > 2:
            print(word, ":", count)
            found = True

    if not found:
        print("No words repeated more than twice.")


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():

    driver = create_driver()

    try:

        print("\nScraping articles...\n")

        articles = scrape_articles(driver)

        print("Saving Spanish articles...")
        save_spanish_articles(articles)

        print("Translating titles...")
        translated_titles = translate_titles(articles)

        print("Saving translated articles...")
        save_translated_articles(articles)

        print("Saving JSON...")
        save_json(articles)

        analyze_words(translated_titles)

        print("\n✅ DONE!")
        print("Files created:")
        print("• spanish_articles.txt")
        print("• translated_articles.txt")
        print("• articles.json")
        print("• images/ folder")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
