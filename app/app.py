"""Flask application for AI-Based News Classification and Fake News Detection (placeholder).

Run with (from repository root):

    cd app
    python app.py

This server intentionally does not import or require any ML model files — it
uses placeholder functions in placeholder_models.py and utilities in utils.py.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os

from placeholder_models import classify_article, detect_fake_news
from utils import clean_text, read_text_file

ALLOWED_EXTENSIONS = {"txt", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/classify", methods=["GET", "POST"])
def classify():
    if request.method == "POST":
        text = request.form.get("article_text", "")
        file = request.files.get("file_upload")

        if not text and (file is None or file.filename == ""):
            flash("Please paste text or upload a .txt/.pdf file.", "warning")
            return redirect(url_for("classify"))

        if file and file.filename != "":
            if not allowed_file(file.filename):
                flash("Invalid file type — only .txt and .pdf are accepted in this demo.", "danger")
                return redirect(url_for("classify"))
            # Process file — read_text_file returns placeholder for PDF
            content = read_text_file(file)
            if not content:
                flash("Failed to read uploaded file.", "danger")
                return redirect(url_for("classify"))
            text = content

        text = clean_text(text)
        if text == "":
            flash("Input is empty after cleaning — please provide more content.", "warning")
            return redirect(url_for("classify"))

        # Placeholder model call
        result = classify_article(text)

        # If model not implemented, flash notice
        flash("Model not available — returning placeholder output.", "info")

        return render_template("result.html", title="Classification result", result=result)

    return render_template("classify.html")


@app.route("/detect", methods=["GET", "POST"])
def detect():
    if request.method == "POST":
        text = request.form.get("news_text", "")
        file = request.files.get("file_upload")

        if not text and (file is None or file.filename == ""):
            flash("Please paste text or upload a .txt/.pdf file.", "warning")
            return redirect(url_for("detect"))

        if file and file.filename != "":
            if not allowed_file(file.filename):
                flash("Invalid file type — only .txt and .pdf are accepted in this demo.", "danger")
                return redirect(url_for("detect"))
            content = read_text_file(file)
            if not content:
                flash("Failed to read uploaded file.", "danger")
                return redirect(url_for("detect"))
            text = content

        text = clean_text(text)
        if text == "":
            flash("Input is empty after cleaning — please provide more content.", "warning")
            return redirect(url_for("detect"))

        result = detect_fake_news(text)
        flash("Fake news detection is a placeholder — model integration pending.", "info")
        return render_template("result.html", title="Fake news detection result", result=result)

    return render_template("detect.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    # Launch dev server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
