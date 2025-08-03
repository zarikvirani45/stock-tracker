from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import os
import requests
from threading import Timer
from difflib import get_close_matches

app = Flask(__name__)
CORS(app)

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "your_newsapi_key_here")
latest_news = []

def fetch_news():
    global latest_news
    try:
        if not NEWS_API_KEY or NEWS_API_KEY == "your_newsapi_key_here":
            latest_news = get_fallback_news()
            return

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
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok':
                latest_news = [
                    {
                        'title': a['title'],
                        'description': a.get('description', ''),
                        'url': a['url'],
                        'source': a['source']['name'],
                        'publishedAt': a['publishedAt'],
                        'urlToImage': a.get('urlToImage', '')
                    }
                    for a in data.get('articles', []) if a.get('title')
                ]
        else:
            latest_news = get_fallback_news()
    except Exception:
        latest_news = get_fallback_news()

    Timer(60.0, fetch_news).start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/stock-data', methods=['POST'])
def stock_data():
    data = request.get_json()
    user_input = data.get("symbol", "").strip()
    range_code = data.get("range", "1mo")

    def resolve_symbol(user_input):
        try:
            search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={user_input}"
            res = requests.get(search_url, timeout=5)
            results = res.json().get("quotes", [])
            if results:
                symbols = [r["symbol"] for r in results if "symbol" in r]
                names = [r["shortname"] for r in results if "shortname" in r]
                matches = get_close_matches(user_input.lower(), names + symbols, n=1, cutoff=0.3)
                if matches:
                    for r in results:
                        if r.get("symbol") and (r.get("shortname", "").lower() == matches[0] or r["symbol"].lower() == matches[0]):
                            ticker = yf.Ticker(r["symbol"])
                            return r["symbol"].upper(), ticker.info
        except:
            pass

        return None, None

    symbol, info = resolve_symbol(user_input)

    if not symbol or not info:
        return jsonify({"error": "Invalid company name or stock symbol."})

    try:
        ticker = yf.Ticker(symbol)

        current_price = info.get("currentPrice", None) or info.get("regularMarketPrice", None)
        if current_price is None:
            return jsonify({"error": "Invalid stock symbol or data unavailable."})

        end_date = datetime.today()
        range_map = {
            "1d": timedelta(days=1),
            "3d": timedelta(days=3),
            "5d": timedelta(days=5),
            "1wk": timedelta(weeks=1),
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
            start_date = end_date - range_map[range_code]
            hist = ticker.history(start=start_date, end=end_date)

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
            "percent_change": percent_change,
            "positive": percent_change >= 0
        }

        return jsonify(stock_summary)

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/trending')
def trending():
    try:
        trending_symbols = ["AMD", "GOOGL", "META", "AAPL", "NVDA", "VOO", "VTI", "TSLA", "MSFT", "AMZN"]
        trending_data = []

        for symbol in trending_symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                price = (info.get("currentPrice") or 
                         info.get("regularMarketPrice") or 
                         info.get("previousClose"))

                if price is not None:
                    trending_data.append({"symbol": symbol, "price": round(float(price), 2)})

            except Exception as symbol_error:
                print(f"Error fetching {symbol}: {str(symbol_error)}")
                continue

        if not trending_data:
            fallback_tickers = [
                {"symbol": "AAPL", "price": 195.00},
                {"symbol": "GOOGL", "price": 2800.00},
                {"symbol": "MSFT", "price": 420.00},
                {"symbol": "TSLA", "price": 250.00},
                {"symbol": "NVDA", "price": 875.00},
                {"symbol": "META", "price": 485.00},
                {"symbol": "AMZN", "price": 155.00},
                {"symbol": "AMD", "price": 140.00}
            ]
            return jsonify(fallback_tickers)

        return jsonify(trending_data)

    except Exception as e:
        print(f"Error in trending route: {str(e)}")
        fallback_tickers = [
            {"symbol": "AAPL", "price": 195.00},
            {"symbol": "GOOGL", "price": 2800.00},
            {"symbol": "MSFT", "price": 420.00},
            {"symbol": "TSLA", "price": 250.00},
            {"symbol": "NVDA", "price": 875.00},
            {"symbol": "META", "price": 485.00},
            {"symbol": "AMZN", "price": 155.00},
            {"symbol": "AMD", "price": 140.00}
        ]
        return jsonify(fallback_tickers)

@app.route('/news')
def get_news():
    return jsonify(latest_news)

def get_fallback_news():
    return [
        {
            'title': "Stock Market Shows Mixed Results in Today's Trading Session",
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

if __name__ == '__main__':
    fetch_news()
    port = int(os.environ.get("PORT", 5051))
    app.run(debug=True, host='0.0.0.0', port=port)

