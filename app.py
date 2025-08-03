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
        
        # Try currentPrice, else fallback to regularMarketPrice for ETFs
        current_price = info.get("currentPrice", None) or info.get("regularMarketPrice", None)
        if current_price is None:
            return jsonify({"error": "Invalid stock symbol or data unavailable."})
        
        end_date = datetime.today()
        
        # Updated range_map with all 11 timeframes
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
            "percent_change": percent_change
        }
        
        return jsonify(stock_summary)
    
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/trending')
def trending():
    """Route to get trending stock prices for the ticker bar"""
    try:
        # Popular stocks for the ticker bar
        trending_symbols = ["AMD", "GOOGL", "META", "AAPL", "NVDA", "VOO", "VTI", "TSLA", "MSFT", "AMZN"]
        trending_data = []
        
        for symbol in trending_symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                
                price = (info.get("currentPrice", None) or 
                        info.get("regularMarketPrice", None) or 
                        info.get("previousClose", None))
                
                if price is not None:
                    trending_data.append({
                        "symbol": symbol, 
                        "price": round(float(price), 2)
                    })
                    
            except Exception as symbol_error:
                print(f"Error fetching {symbol}: {str(symbol_error)}")
                continue
        
        
        if not trending_data:
            # Fallback data if yfinance fails
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
        # Return fallback data on any error
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
    """Route to get financial news"""
    try:
        # Check if API key is properly set
        if not NEWS_API_KEY or NEWS_API_KEY == "your_newsapi_key_here":
            print("NewsAPI key not set properly. Using fallback news.")
            return get_fallback_news()
        
       
        url = f"https://newsapi.org/v2/everything"
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
            try:
                news_data = response.json()
                
                
                if news_data.get('status') == 'error':
                    print(f"NewsAPI error: {news_data.get('message', 'Unknown error')}")
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
            except ValueError as json_error:
                print(f"JSON parsing error: {str(json_error)}")
                print(f"Response content: {response.text[:200]}...")
                return get_fallback_news()
        else:
            print(f"HTTP error {response.status_code}: {response.text[:200]}...")
            return get_fallback_news()
    
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return get_fallback_news()

def get_fallback_news():
    """Fallback function to provide sample financial news when API fails"""
    try:
        # Sample financial news with updated timestamps
        fallback_articles = [
            {
                'title': 'Stock Market Shows Mixed Results in Today\'s Trading Session',
                'description': 'Major indices display varied performance as investors digest latest economic data and corporate earnings reports.',
                'url': 'https://finance.yahoo.com',
                'source': 'Financial News',
                'publishedAt': datetime.now().isoformat(),
                'urlToImage': ''
            },
            {
                'title': 'Tech Stocks Lead Market Volatility Amid Interest Rate Concerns',
                'description': 'Technology sector experiences heightened volatility as market participants assess Federal Reserve policy implications.',
                'url': 'https://finance.yahoo.com',
                'source': 'Market Watch',
                'publishedAt': (datetime.now() - timedelta(hours=1)).isoformat(),
                'urlToImage': ''
            },
            {
                'title': 'Economic Indicators Point to Continued Market Uncertainty',
                'description': 'Latest economic data releases suggest ongoing market volatility as investors navigate changing economic conditions.',
                'url': 'https://finance.yahoo.com',
                'source': 'Economic Times',
                'publishedAt': (datetime.now() - timedelta(hours=2)).isoformat(),
                'urlToImage': ''
            },
            {
                'title': 'Energy Sector Gains Momentum in Current Trading Week',
                'description': 'Energy stocks show strong performance as commodity prices stabilize and demand outlook improves.',
                'url': 'https://finance.yahoo.com',
                'source': 'Energy News',
                'publishedAt': (datetime.now() - timedelta(hours=3)).isoformat(),
                'urlToImage': ''
            },
            {
                'title': 'Banking Sector Responds to Latest Federal Reserve Communications',
                'description': 'Financial institutions adjust strategies following recent Federal Reserve statements on monetary policy direction.',
                'url': 'https://finance.yahoo.com',
                'source': 'Banking Today',
                'publishedAt': (datetime.now() - timedelta(hours=4)).isoformat(),
                'urlToImage': ''
            },
            {
                'title': 'Cryptocurrency Markets Show Renewed Interest from Institutional Investors',
                'description': 'Digital asset markets experience increased institutional participation as regulatory clarity improves.',
                'url': 'https://finance.yahoo.com',
                'source': 'Crypto Finance',
                'publishedAt': (datetime.now() - timedelta(hours=5)).isoformat(),
                'urlToImage': ''
            },
            {
                'title': 'Manufacturing Data Suggests Economic Resilience Despite Headwinds',
                'description': 'Industrial production figures indicate continued strength in manufacturing sector across multiple regions.',
                'url': 'https://finance.yahoo.com',
                'source': 'Industrial Report',
                'publishedAt': (datetime.now() - timedelta(hours=6)).isoformat(),
                'urlToImage': ''
            },
            {
                'title': 'Consumer Spending Patterns Shift as Economic Conditions Evolve',
                'description': 'Retail data shows changing consumer preferences and spending habits in response to current economic climate.',
                'url': 'https://finance.yahoo.com',
                'source': 'Consumer Insights',
                'publishedAt': (datetime.now() - timedelta(hours=7)).isoformat(),
                'urlToImage': ''
            }
        ]
        
        return jsonify(fallback_articles)
    
    except Exception as e:
        print(f"Error in fallback news: {str(e)}")
        return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5051)) 
    app.run(debug=True, host='0.0.0.0', port=port)