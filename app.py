from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import os  # <-- Import os for env vars

app = Flask(__name__)
CORS(app)

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
        range_map = {
            "1d": timedelta(days=1),
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
    try:
        trending_symbols = ["AMD", "GOOGL", "META", "AAPL", "NVDA", "VOO", "VTI", "TSLA", "MSFT", "AMZN"]
        trending_data = []

        for symbol in trending_symbols:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get("currentPrice", None) or info.get("regularMarketPrice", None)
            if price is not None:
                trending_data.append({"symbol": symbol, "price": round(price, 2)})

        return jsonify(trending_data)

    except Exception as e:
        return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5051))  # Dynamically get port or default to 5051
    app.run(debug=True, host='0.0.0.0', port=port)
