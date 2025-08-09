from dotenv import load_dotenv
load_dotenv() 
import os
import mysql.connector
from datetime import datetime, timedelta, time
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import yfinance as yf
import requests
from urllib.parse import urlparse  # <-- Added for parsing MYSQL_URL
import pytz

app = Flask(__name__)
CORS(app)

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "your_newsapi_key_here")

mysql_url = os.environ.get("MYSQL_URL")
parsed_url = urlparse(mysql_url) if mysql_url else None

db_config = {
    'host': parsed_url.hostname if parsed_url else os.environ.get("MYSQLHOST"),
    'user': parsed_url.username if parsed_url else os.environ.get("MYSQLUSER"),
    'password': parsed_url.password if parsed_url else os.environ.get("MYSQLPASSWORD"),
    'database': parsed_url.path.lstrip('/') if parsed_url else os.environ.get("MYSQLDATABASE"),
    'port': parsed_url.port if parsed_url else int(os.environ.get("MYSQLPORT", 3306))
}
# -------------------------------------------------------------

def log_user_action(action, symbol=None):
    print(f"[Logging to DB] Action: {action}, Symbol: {symbol}")  
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                action VARCHAR(255),
                symbol VARCHAR(10),
                timestamp DATETIME
            )
        """)
        cursor.execute(
            "INSERT INTO user_logs (action, symbol, timestamp) VALUES (%s, %s, %s)",
            (action, symbol, datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[DB Logging Error] {e}")

def get_db_connection():
    return mysql.connector.connect(**db_config)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ip VARCHAR(100),
                timestamp DATETIME
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_searches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(10),
                search_time DATETIME,
                ip VARCHAR(100),
                range_code VARCHAR(10)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error initializing DB:", e)

init_db()

@app.route('/')
def home():
    log_user_action("page load")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO visits (ip, timestamp) VALUES (%s, %s)", (request.remote_addr, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error logging visit:", e)
    return render_template('index.html')

@app.route('/stock-data', methods=['POST'])
def stock_data():
    data = request.get_json()
    symbol = data.get("symbol", "").upper()
    log_user_action("search_stock", symbol)
    range_code = data.get("range", "1mo")
    try:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stock_searches (symbol, range_code, search_time, ip) VALUES (%s, %s, %s, %s)",
                (symbol, range_code, datetime.now(), request.remote_addr)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print("Error logging search:", e)

        ticker = yf.Ticker(symbol)
        info = ticker.info

        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if current_price is None:
            return jsonify({"error": "Invalid stock symbol or data unavailable."})

        end_date = datetime.today()

        range_map = {
            "1d": timedelta(days=1),
            "3d": timedelta(days=3),
            "1wk": timedelta(weeks=1),
            "3wk": timedelta(weeks=3),
            "1mo": timedelta(weeks=4),
            "3mo": timedelta(weeks=12),
            "6mo": timedelta(weeks=26),
            "1y": timedelta(weeks=52),
            "3y": timedelta(weeks=156),
            "5y": timedelta(weeks=260),
            "max": None
        }

        eastern = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern)
        weekday = now_et.weekday()
        market_open_time = time(9, 30)
        market_close_time = time(16, 0)

        if range_code == "1d":
            print("selected 1d")
            # get intraday data first
            hist = ticker.history(period="1d", interval="5m")
            
            # if no intraday data, fallback to recent daily data
            if hist.empty:
                hist = ticker.history(period="5d", interval="1d")
                if not hist.empty:
                    hist = hist.tail(1)  # get most recent day

        else:
            if range_code == "max":
                hist = ticker.history(period="max")
            else:
                start_date = end_date - range_map.get(range_code, timedelta(weeks=4))
                hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))

        hist = hist.dropna()
        if hist.empty:
            return jsonify({"error": "No historical data found for this range."})

        if range_code == "1d" and len(hist) > 20: 
            dates = hist.index.strftime('%H:%M').tolist()
        else:
            dates = hist.index.strftime('%Y-%m-%d').tolist()
        prices = hist['Close'].round(2).tolist()

        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        absolute_change = round(end_price - start_price, 2)
        percent_change = round(((end_price - start_price) / start_price) * 100, 2)

        stock_summary = {
            "symbol": symbol,
            "name": info.get("shortName", "N/A"),
            "current_price": current_price,
            "day_high": info.get("dayHigh", "N/A"),
            "day_low": info.get("dayLow", "N/A"),
            "high_52week": info.get("fiftyTwoWeekHigh", "N/A"),
            "low_52week": info.get("fiftyTwoWeekLow", "N/A"),
            "dates": dates,
            "prices": prices,
            "absolute_change": absolute_change,
            "percent_change": percent_change
        }

        print('stock summary: ')
        print(stock_summary)

        return jsonify(stock_summary)

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/live-ticker')
def live_ticker():
    symbols = ["AAPL", "NVDA", "MSFT", "META", "TSLA", "AMZN", "AMD", "GOOG", "PLTR"]
    results = []

    try:
        tickers = yf.Tickers(' '.join(symbols)).tickers

        for symbol in symbols:
            info = tickers[symbol].info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if price is not None:
                results.append({
                    "symbol": symbol,
                    "price": round(price, 2)
                })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve ticker data: {str(e)}"})

@app.route('/news')
def get_news():
    if not NEWS_API_KEY or NEWS_API_KEY == "your_newsapi_key_here":
        print("NewsAPI key not set properly. Using fallback news.")
        return get_fallback_news()

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'apiKey': NEWS_API_KEY,
            'sources': 'cnbc,bloomberg,reuters,the-wall-street-journal,financial-times',
            'q': 'stock market OR finance OR economy OR trading',
            'sortBy': 'publishedAt',
            'pageSize': 10,
            'language': 'en'
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print(f"News API returned status {response.status_code}")
            return get_fallback_news()

        news_data = response.json()
        if news_data.get('status') == 'error':
            print(f"NewsAPI error: {news_data.get('message')}")
            return get_fallback_news()

        articles = []
        for article in news_data.get('articles', []):
            if article.get('title') and article.get('url') and article.get('publishedAt'):
                articles.append({
                    'title': article['title'],
                    'description': article.get('description', ''),
                    'url': article['url'],
                    'source': article['source']['name'],
                    'publishedAt': article['publishedAt'],
                    'urlToImage': article.get('urlToImage', '')
                })

        return jsonify(articles)

    except Exception as e:
        print(f"Error fetching news: {e}")
        return get_fallback_news()

def get_fallback_news():
    fallback_articles = [
        {
            'title': 'Stock Market Shows Mixed Results in Today\'s Trading Session',
            'description': 'Major indices display varied performance...',
            'url': 'https://finance.yahoo.com',
            'source': 'Financial News',
            'publishedAt': datetime.now().isoformat(),
            'urlToImage': ''
        },
        {
            'title': 'Tech Stocks Lead Market Volatility Amid Interest Rate Concerns',
            'description': 'Technology sector experiences heightened volatility...',
            'url': 'https://finance.yahoo.com',
            'source': 'Market Watch',
            'publishedAt': (datetime.now() - timedelta(hours=1)).isoformat(),
            'urlToImage': ''
        }
    ]
    return jsonify(fallback_articles)

if __name__ == '__main__':
    init_db() 
    port = int(os.environ.get("PORT", 5051))
    app.run(debug=True, host='0.0.0.0', port=port)
