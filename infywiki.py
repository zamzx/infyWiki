import wikipediaapi
from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup

# Initialize Flask and Wikipedia API
app = Flask(__name__)
wikipedia = wikipediaapi.Wikipedia(user_agent="YourAppName/1.0 (your@email.com)", language="en")

# Keep track of loaded articles
loaded_articles = []

# Get first article
def get_first_article():
    return "A"  # Start from the article titled "A"

# Get next article
def get_next_article(title):
    global loaded_articles

    # Fetch the category of the current article
    category_titles = list(wikipedia.page(title).categories.keys())
    
    if category_titles:
        category = category_titles[0]  # Pick the first category
        category_page = wikipedia.page(category)
        all_pages = sorted(category_page.categorymembers.keys())  # Get sorted article titles
        
        # Filter out articles already loaded
        remaining_pages = [p for p in all_pages if p not in loaded_articles]
        
        if remaining_pages:
            next_title = remaining_pages[0]  # Get the first unseen article
            loaded_articles.append(next_title)  # Mark it as loaded
            return next_title

    return None

# Get images from the Wikipedia page (extract URLs)
def get_page_images(page):
    url = f"https://en.wikipedia.org/wiki/{page}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all image tags
    images = soup.find_all('img')

    # Extract image URLs from src attribute
    image_urls = ['https:' + img['src'] for img in images if img.get('src')]
    return image_urls

# Fetch Wikipedia raw HTML content directly
def get_raw_html_content(page):
    url = f"https://en.wikipedia.org/wiki/{page}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the main content of the article, usually in <div class="mw-parser-output">
    main_content = soup.find('div', {'class': 'mw-parser-output'})
    
    # Remove citations or footnotes (elements like <sup>, <span>, etc.)
    for citation in main_content.find_all(['sup', 'span', 'div'], class_='reference'):
        citation.decompose()  # Remove the citation element
    
    # Return the cleaned up raw HTML content
    return str(main_content) if main_content else str(soup)  # Return the content or entire page if not found

@app.route('/')
def index():
    first_article = get_first_article()
    html_content = get_raw_html_content(first_article)  # Get raw HTML content
    return render_template_string(TEMPLATE, title=first_article, content=html_content, images=get_page_images(first_article))


@app.route('/next', methods=['POST'])
def next_article():
    current_title = request.json.get('current_title')
    next_title = get_next_article(current_title)
    if next_title:
        html_content = get_raw_html_content(next_title)  # Get raw HTML content for the next article
        return render_template_string(TEMPLATE, title=next_title, content=html_content, images=get_page_images(next_title))
    return jsonify({'title': None, 'content': "No more articles found.", 'images': []})


TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Infinite Wikipedia</title>
    <script>
        function loadNextArticle() {
            fetch('/next', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({current_title: document.getElementById('title').innerText})
            })
            .then(response => response.text())  // Expect HTML response, not JSON
            .then(data => {
                let container = document.getElementById('article-container');
                container.innerHTML += data;  // Append new content without resetting page
                setupScrollListener();  // Re-setup the scroll listener after loading new content
            });
        }

        function setupScrollListener() {
            window.onscroll = function() {
                if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 5) {
                    loadNextArticle();
                }
            }
        }

        // Setup the scroll listener when the page loads
        window.onload = function() {
            setupScrollListener();
        };
    </script>
</head>
<body>
    <div id="article-container">
        <h2 id='title'>{{ title }}</h2>
        <div>{{ content | safe }}</div>  <!-- Render raw HTML with proper formatting -->
        {% for img in images %}
            <img src="{{ img }}" style="max-width:100%;"><br>
        {% endfor %}
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)
