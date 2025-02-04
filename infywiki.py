from flask import Flask, render_template_string, request, jsonify
import wikipediaapi

app = Flask(__name__)
wikipedia = wikipediaapi.Wikipedia(user_agent="YourAppName/1.0 (your@email.com)", language="en")

loaded_articles = []  # Track loaded articles

def get_first_article():
    return "A"  # Start from article "A"

def get_next_article(title):
    global loaded_articles

    try:
        page = wikipedia.page(title)

        # Get actual linked articles, ignoring categories
        linked_articles = [link for link in page.links.keys() if not link.startswith("Category:")]

        remaining_articles = [p for p in linked_articles if p not in loaded_articles]

        if remaining_articles:
            next_title = remaining_articles[0]  # Get the first valid article
            loaded_articles.append(next_title)
            return next_title
    except Exception as e:
        print(f"Error getting next article: {e}")

    return None

@app.route('/')
def index():
    first_article = get_first_article()
    return render_template_string(TEMPLATE, title=first_article, iframe_url=f"https://en.wikipedia.org/wiki/{first_article}")

@app.route('/next', methods=['POST'])
def next_article():
    current_title = request.json.get('current_title')
    next_title = get_next_article(current_title)

    if next_title:
        return jsonify({'title': next_title, 'iframe_url': f"https://en.wikipedia.org/wiki/{next_title}"})

    return jsonify({'title': None, 'iframe_url': None})

# Updated HTML Template
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Infinite Wikipedia</title>
    <script>
        function loadNextArticle() {
            let currentFrames = document.querySelectorAll('iframe');
            let lastFrame = currentFrames[currentFrames.length - 1];

            if (lastFrame) {
                let rect = lastFrame.getBoundingClientRect();
                if (rect.bottom < window.innerHeight + 50) {
                    fetch('/next', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({current_title: lastFrame.getAttribute('data-title')})
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.title) {
                            let iframe = document.createElement('iframe');
                            iframe.src = data.iframe_url;
                            iframe.width = "100%";
                            iframe.height = "800px";
                            iframe.setAttribute('data-title', data.title);
                            iframe.style.border = "none";
                            iframe.style.display = "block";
                            iframe.style.marginTop = "10px";

                            document.body.appendChild(iframe);
                        }
                    });
                }
            }
        }

        window.addEventListener('scroll', () => {
            requestAnimationFrame(loadNextArticle);
        });

        document.addEventListener('DOMContentLoaded', loadNextArticle);
    </script>
</head>
<body>
    <h2>{{ title }}</h2>
    <iframe src="{{ iframe_url }}" width="100%" height="800px" style="border:none; display:block;" data-title="{{ title }}"></iframe>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)
