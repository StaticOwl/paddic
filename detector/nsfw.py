import re
import os

from bs4 import BeautifulSoup
from huggingface_hub import login
from transformers import pipeline

login(token=os.environ["HF_WRITE_TOKEN"])

text_pipe = pipeline("text-classification", model="eliasalbouzidi/distilbert-nsfw-text-classifier")

def extract_text_from_html(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text().strip().replace("\n", " ")

def is_nsfw_text(text):
    if not text:
        return False

    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    chunks = [text[i: i+512] for i in range(0, len(text), 512)]

    for chunk in chunks:
        result = text_pipe(chunk)
        if any(res["label"] == "nsfw" and res["score"] > 0.7 for res in result):  # Lower threshold slightly
            return True

    return False

