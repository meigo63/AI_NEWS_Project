import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
# Load dataset
df = pd.read_csv("fake_news_dataset (1).csv")

# Clean text
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

df['cleaned'] = df['text'].apply(clean_text)

print("Data cleaned successfully ✅")
df.to_csv("D:\AI_NEWS_Project\Processed_data\cleaned_fake_news_dataset (1).csv", index=False)

