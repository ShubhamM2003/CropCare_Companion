import nltk
nltk.download('stopwords')

from nltk.corpus import stopwords

# Example usage
stop_words = set(stopwords.words('english'))
print(stop_words)