# AI-Based News Classification & Fake News Detection (Placeholder Web App)

This repository contains a lightweight Flask web application scaffold for a
graduation project. The UI, routes, placeholders, and utilities are ready —
no machine learning models are required or loaded.

How to run (dev):

1. Open a terminal
2. Change directory into the app folder:

```bash
cd app
python app.py
```

3. Open http://localhost:5000 in your browser.

What is included:
- /app/app.py — Flask app (routes and web server)
- /app/placeholder_models.py — deterministic placeholder functions (no models)
- /app/utils.py — minimal text cleaning and file helpers
- /app/templates — HTML templates (base, index, classify, detect, result, 404)
- /app/static/css/style.css — small custom styles
- /app/requirements.txt — required packages

Design notes:
- The app uses Bootstrap via CDN for a modern UI
- File uploads accept .txt/.pdf but PDF reading is intentionally a placeholder
  to avoid adding heavy dependencies before model integration.

Next steps for integration:
- Replace functions in `placeholder_models.py` with model loading code
- Add explainability integration (LIME/SHAP) and route(s) to render them
- Extend `utils.read_text_file()` to use PDF parsing libraries when needed
