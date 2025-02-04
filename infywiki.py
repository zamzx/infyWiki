from flask import Flask, render_template_string, request, jsonify
import wikipedia
import requests
import warnings
from bs4 import GuessedAtParserWarning
from wikipedia.exceptions import DisambiguationError, PageError

# Disable BeautifulSoup parser warnings
warnings.filterwarnings("ignore", category=GuessedAtParserWarning)

app = Flask(__name__)

# Configure Wikipedia language and user agent
wikipedia.set_lang("en")
user_agent = "WikiFlow/1.0 (jelnique@gmail.com)"
wikipedia.set_user_agent(user_agent)

# A set to keep track of pages that have already been loaded
visited_pages = set()

# Global variables to cache search results
cached_search_results = []
current_search_term = ""
current_search_index = 0

def get_wikipedia_page(title, visited=None):
    """
    Attempts to fetch a Wikipedia page for a given title.
    If a DisambiguationError is raised, iterates through the options,
    skipping those containing 'disambiguation' and avoiding loops.
    """
    if visited is None:
        visited = set()
    if title in visited:
        print(f"Already visited '{title}', stopping recursion.")
        return None
    visited.add(title)
    try:
        # Use auto_suggest=False for a more exact match
        page = wikipedia.page(title, auto_suggest=False)
        return page
    except DisambiguationError as e:
        print(f"Disambiguation error for '{title}': {e.options}")
        # Try each option that does not contain "disambiguation"
        for option in e.options:
            if "disambiguation" in option.lower():
                continue
            candidate = get_wikipedia_page(option, visited)
            if candidate:
                return candidate
        print(f"No suitable disambiguation found for '{title}'")
        return None
    except PageError as e:
        print(f"Page error for '{title}': {e}")
        return None

@app.route('/search', methods=['POST'])
def search():
    """
    Performs a search using the provided term and caches a list of titles.
    Returns the first two valid articles from the cached results.
    """
    global current_search_term, cached_search_results, current_search_index, visited_pages
    search_term = request.json.get('search_term')
    if not search_term:
        return jsonify({'articles': []})
    
    current_search_term = search_term
    try:
        # Get up to 50 search results for better filtering options
        results = wikipedia.search(search_term, results=50)
    except Exception as e:
        print("Search error:", e)
        return jsonify({'articles': []})
    
    cached_search_results = results
    current_search_index = 0  # reset the index for a new search
    articles = []
    
    # Loop through cached results until we have two valid articles
    while current_search_index < len(cached_search_results) and len(articles) < 2:
        title = cached_search_results[current_search_index]
        current_search_index += 1
        page = get_wikipedia_page(title)
        if page and page.title not in visited_pages:
            articles.append({
                'title': page.title,
                'url': f"https://en.wikipedia.org/wiki/{page.title.replace(' ', '_')}"
            })
            visited_pages.add(page.title)
    return jsonify({'articles': articles})

@app.route('/next_article', methods=['POST'])
def next_article():
    """
    Returns the next two valid articles from the cached search results.
    """
    global current_search_term, cached_search_results, current_search_index, visited_pages
    if not current_search_term:
        return jsonify({'articles': []})
    
    articles = []
    while current_search_index < len(cached_search_results) and len(articles) < 2:
        title = cached_search_results[current_search_index]
        current_search_index += 1
        page = get_wikipedia_page(title)
        if page and page.title not in visited_pages:
            articles.append({
                'title': page.title,
                'url': f"https://en.wikipedia.org/wiki/{page.title.replace(' ', '_')}"
            })
            visited_pages.add(page.title)
    return jsonify({'articles': articles})

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

def is_valid_article(title):
    """
    A basic validation to rule out empty or purely numeric titles.
    (Spaces are allowed since most Wikipedia articles include them.)
    """
    return bool(title) and not title.isdigit()

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WikiFlow - Infinite Wikipedia</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
    #search-container {
      position: fixed; top: 0; left: 0; width: 100%; background: white;
      padding: 10px; box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.2);
      text-align: center; z-index: 1000;
    }
    #search-container input { padding: 8px; font-size: 16px; width: 250px; }
    #current-title { font-size: 18px; font-weight: bold; margin-top: 5px; }
    #content { margin-top: 80px; display: flex; flex-direction: column; align-items: center; }
    iframe { width: 90%; height: 800px; border: none; margin-bottom: 10px; }
    #loading { display: none; text-align: center; margin-top: 10px; }
  </style>
</head>
<body>

  <div id="search-container">
    <input type="text" id="search" placeholder="Search Wikipedia">
    <button onclick="searchArticle()">Search</button>
    <div id="current-title">Welcome! Search an article.</div>
  </div>

  <div id="loading">
    <p>Loading next articles...</p>
  </div>

  <div id="content"></div>

  <script>
    let loadedPages = new Set();
    let isLoading = false;

    // Set up an IntersectionObserver to update the current article title.
    let observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        // If the iframe is at least 50% visible, update the title.
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          const title = entry.target.dataset.title;
          document.getElementById('current-title').textContent = 'Reading: ' + title;
        }
      });
    }, { threshold: 0.5 });

    function searchArticle() {
      const searchTerm = document.getElementById('search').value;
      if (searchTerm.trim() === '') return;
      // Clear loaded pages for a new search
      loadedPages = new Set();
      fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search_term: searchTerm })
      })
      .then(response => response.json())
      .then(data => {
        document.getElementById('content').innerHTML = '';  // Clear previous results
        if (data.articles.length > 0) {
          data.articles.forEach(article => loadIframe(article.title, article.url));
          // Set the title to the first article
          document.getElementById('current-title').textContent = 'Reading: ' + data.articles[0].title;
        } else {
          alert('No results found!');
        }
      })
      .catch(error => console.error('Error fetching search results:', error));
    }

    function loadIframe(title, url) {
      if (loadedPages.has(title)) return;  // Skip if already loaded
      const iframe = document.createElement('iframe');
      iframe.src = url;
      iframe.dataset.title = title;
      document.getElementById('content').appendChild(iframe);
      loadedPages.add(title);
      // Observe this iframe so that when it's mostly in view, the title updates.
      observer.observe(iframe);
    }

    function loadNextArticles() {
      if (isLoading) return;
      const isAtBottom = (window.innerHeight + window.scrollY) >= document.body.offsetHeight - 10;
      if (isAtBottom) {
        isLoading = true;
        document.getElementById('loading').style.display = 'block';
        fetch('/next_article', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
          data.articles.forEach(article => loadIframe(article.title, article.url));
        })
        .finally(() => {
          document.getElementById('loading').style.display = 'none';
          isLoading = false;
        });
      }
    }

    window.onscroll = loadNextArticles;
  </script>

</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)
