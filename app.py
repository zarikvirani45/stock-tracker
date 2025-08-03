from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)
CORS(app)

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "your_newsapi_key_here")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/stock-data', methods=['POST'])
def stock_data():
    data = request.get_json()
    symbol = data.get("symbol", "").upper()
    range_code = data.get("range", "1mo")

    try:
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

        if range_code == "max":
            hist = ticker.history(period="max")
        else:
            start_date = end_date - range_map.get(range_code, timedelta(weeks=4))
            hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))

        hist = hist.dropna()
        if hist.empty:
            return jsonify({"error": "No historical data found for this range."})

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

        return jsonify(stock_summary)

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/tickers')
def ticker_prices():
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
    port = int(os.environ.get("PORT", 5051))
    app.run(debug=True, host='0.0.0.0', port=port)