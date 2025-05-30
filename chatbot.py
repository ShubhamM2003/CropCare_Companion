from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from botConfig import myBotName, chatBG, botAvatar
import pandas as pd
import nltk
nltk.download('punkt_tab')
from nltk.corpus import stopwords
nltk.download('stopwords')
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn import metrics
from googletrans import Translator
import random
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import requests
import json

application = Flask(__name__)
application.secret_key = 'your-secret-key-here'  # Change this to a random secret key

chatbotName = myBotName
print("Bot Name set to: " + chatbotName)
print("Background is " + chatBG)
print("Avatar is " + botAvatar)

# OpenRouter API configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize database
def init_db():
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Load data from CSV file
data = pd.read_csv('Datasets/Final_PreProcessed_Dataset.csv')

# Preprocess the data
stop_words = set(stopwords.words('english'))
ps = PorterStemmer()

def preprocess_questions(questions):
    # Tokenize questions
    words = word_tokenize(questions.lower())
    # Remove stop words
    words = [w for w in words if not w in stop_words]
    # Stem words
    words = [ps.stem(w) for w in words]
    # Join words back into a string
    return ' '.join(words)

# Apply preprocessing to all questionss in the data
data['questions'] = data['questions'].apply(preprocess_questions)

# Train the chatbot
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# Create a bag-of-words representation of the questionss
vectorizer = CountVectorizer()
X = vectorizer.fit_transform(data['questions'])
y = data['answers']

# Train a Naive Bayes classifier
clf = MultinomialNB()
model = clf.fit(X, y)

# Function to get response from OpenRouter API
def get_api_response(message):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek/deepseek-chat:free",
            "messages": [{"role": "user", "content": message}]
        }
        
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    except Exception as e:
        print(f"API Error: {e}")
        return "I'm sorry, I couldn't process your request at the moment."

# Updated function to get chatbot answers with confidence checking
def get_answers(questions):
    # Preprocess the questions
    questions = preprocess_questions(questions)
    # Convert the questions to a bag-of-words representation
    X_test = vectorizer.transform([questions])
    # Get the predicted answers and probabilities
    predictions = clf.predict(X_test)[0]
    probabilities = clf.predict_proba(X_test)[0]
    confidence = max(probabilities)
    
    # If confidence is low, use API as fallback
    if confidence < 0.3:  # Low confidence threshold
        return get_api_response(questions)
    else:
        return predictions

# Helper functions for authentication
def get_user_by_username(username):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(username, email, password):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                      (username, email, password_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def save_chat_history(user_id, user_message, bot_response):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chat_history (user_id, user_message, bot_response) VALUES (?, ?, ?)',
                  (user_id, user_message, bot_response))
    conn.commit()
    conn.close()

def get_chat_history(user_id):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_message, bot_response, timestamp FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC',
                  (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

# Authentication routes
@application.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = get_user_by_username(username)
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@application.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if create_user(username, email, password):
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username or email already exists!', 'error')
    
    return render_template('signup.html')

@application.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# History route
@application.route("/history")
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    chat_history = get_chat_history(session['user_id'])
    return render_template('history.html', history=chat_history, botName=chatbotName)

# Main routes
@application.route("/")
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", botName=chatbotName, chatBG=chatBG, botAvatar=botAvatar, username=session['username'])

@application.route("/get")
def get_bot_response():
    if 'user_id' not in session:
        return "Please login", 401
    
    userText = request.args.get('msg')
    botReply = get_answers(userText)
    
    # Save to history
    save_chat_history(session['user_id'], userText, botReply)
    
    return botReply

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=5000, debug=True)