"""
Stock Portfolio API Server
Uses yfinance to fetch real-time stock data for Taiwan and US markets
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import json
import requests

app = Flask(__name__)
CORS(app)

# Cache for reducing API calls
price_cache = {}
exchange_rate_cache = {}
CACHE_DURATION = 60  # seconds
EXCHANGE_RATE_CACHE_DURATION = 3600  # 1 hour for exchange rates

def get_cached_or_fetch(symbol, fetch_func):
    """Get data from cache or fetch new data"""
    now = datetime.now()
    if symbol in price_cache:
        cached_time, cached_data = price_cache[symbol]
        if (now - cached_time).seconds < CACHE_DURATION:
            return cached_data

    data = fetch_func(symbol)
    price_cache[symbol] = (now, data)
    return data

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_price(symbol):
    """
    Get current stock price and change
    Supports both US stocks (AAPL) and Taiwan stocks (2330.TW)
    """
    try:
        def fetch_stock(sym):
            ticker = yf.Ticker(sym)
            info = ticker.info
            hist = ticker.history(period='2d')

            if hist.empty:
                return {'error': 'No data available'}

            current_price = hist['Close'].iloc[-1]

            # Calculate change
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100
            else:
                change = 0
                change_percent = 0

            return {
                'symbol': sym,
                'price': round(float(current_price), 2),
                'change': round(float(change), 2),
                'changePercent': round(float(change_percent), 2),
                'currency': info.get('currency', 'USD'),
                'name': info.get('longName', sym),
                'timestamp': datetime.now().isoformat()
            }

        data = get_cached_or_fetch(symbol, fetch_stock)
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stocks/batch', methods=['POST'])
def get_batch_stocks():
    """
    Get multiple stock prices in one request
    Body: {"symbols": ["AAPL", "2330.TW", "TSLA"]}
    """
    try:
        symbols = request.json.get('symbols', [])
        results = {}

        for symbol in symbols:
            try:
                def fetch_stock(sym):
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period='2d')

                    if hist.empty:
                        return {'error': 'No data available'}

                    current_price = hist['Close'].iloc[-1]

                    if len(hist) >= 2:
                        prev_close = hist['Close'].iloc[-2]
                        change = current_price - prev_close
                        change_percent = (change / prev_close) * 100
                    else:
                        change = 0
                        change_percent = 0

                    return {
                        'price': round(float(current_price), 2),
                        'change': round(float(change), 2),
                        'changePercent': round(float(change_percent), 2)
                    }

                results[symbol] = get_cached_or_fetch(symbol, fetch_stock)
            except Exception as e:
                results[symbol] = {'error': str(e)}

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/indices', methods=['GET'])
def get_major_indices():
    """Get major market indices"""
    try:
        indices = {
            'TWII': '^TWII',      # Taiwan Weighted Index
            'SPX': '^GSPC',       # S&P 500
            'NASDAQ': '^IXIC',    # Nasdaq
            'DJI': '^DJI'         # Dow Jones
        }

        results = {}
        for name, symbol in indices.items():
            try:
                def fetch_index(sym):
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period='5d')

                    if hist.empty:
                        return {'error': 'No data available'}

                    current_value = hist['Close'].iloc[-1]

                    if len(hist) >= 2:
                        prev_close = hist['Close'].iloc[-2]
                        change = current_value - prev_close
                        change_percent = (change / prev_close) * 100
                    else:
                        change = 0
                        change_percent = 0

                    # OHLCV for expandable card
                    latest = hist.iloc[-1]
                    closes = [round(float(c), 2) for c in hist['Close'].tolist()]

                    return {
                        'value': round(float(current_value), 2),
                        'change': round(float(change), 2),
                        'changePercent': round(float(change_percent), 2),
                        'open': round(float(latest['Open']), 2),
                        'high': round(float(hist['High'].max()), 2),
                        'low': round(float(hist['Low'].min()), 2),
                        'volume': int(latest['Volume']),
                        'closes': closes
                    }

                results[name] = get_cached_or_fetch(symbol, fetch_index)
            except Exception as e:
                results[name] = {'error': str(e)}

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<symbol>', methods=['GET'])
def get_stock_history(symbol):
    """
    Get historical stock data for charts
    Query params: period (1mo, 3mo, 6mo, 1y, 2y, 5y)
    """
    try:
        period = request.args.get('period', '1y')

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return jsonify({'error': 'No data available'}), 404

        # Format data for chart
        data = []
        for index, row in hist.iterrows():
            data.append({
                'date': index.strftime('%Y-%m-%d'),
                'close': round(float(row['Close']), 2),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'volume': int(row['Volume'])
            })

        return jsonify({
            'symbol': symbol,
            'period': period,
            'data': data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/history', methods=['POST'])
def get_portfolio_history():
    """
    Calculate portfolio value history based on holdings
    Body: {
        "holdings": [
            {"symbol": "AAPL", "shares": 10, "avgCost": 150},
            {"symbol": "2330.TW", "shares": 1000, "avgCost": 500}
        ],
        "period": "1y"
    }
    """
    try:
        holdings = request.json.get('holdings', [])
        period = request.json.get('period', '1y')

        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400

        # Fetch historical data for all stocks
        all_history = {}
        for holding in holdings:
            symbol = holding['symbol']
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if not hist.empty:
                all_history[symbol] = hist

        if not all_history:
            return jsonify({'error': 'No historical data available'}), 404

        # Find common dates across all stocks
        date_sets = [set(hist.index.strftime('%Y-%m-%d')) for hist in all_history.values()]
        common_dates = sorted(set.intersection(*date_sets))

        # Calculate portfolio value for each date
        portfolio_history = []
        for date_str in common_dates:
            total_value = 0
            total_cost = 0

            for holding in holdings:
                symbol = holding['symbol']
                shares = holding['shares']
                avg_cost = holding['avgCost']

                if symbol in all_history:
                    hist = all_history[symbol]
                    date_data = hist[hist.index.strftime('%Y-%m-%d') == date_str]

                    if not date_data.empty:
                        close_price = float(date_data['Close'].iloc[0])
                        total_value += close_price * shares
                        total_cost += avg_cost * shares

            if total_value > 0:
                pnl = total_value - total_cost
                pnl_percent = (pnl / total_cost) * 100

                portfolio_history.append({
                    'date': date_str,
                    'value': round(total_value, 2),
                    'cost': round(total_cost, 2),
                    'pnl': round(pnl, 2),
                    'pnlPercent': round(pnl_percent, 2)
                })

        return jsonify({
            'period': period,
            'data': portfolio_history
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/exchange-rate', methods=['GET'])
def get_exchange_rate():
    """
    Get USD to TWD exchange rate
    Uses exchangerate-api.io free tier (no API key needed for basic usage)
    """
    try:
        # Check cache first
        now = datetime.now()
        if 'USDTWD' in exchange_rate_cache:
            cached_time, cached_rate = exchange_rate_cache['USDTWD']
            if (now - cached_time).seconds < EXCHANGE_RATE_CACHE_DURATION:
                return jsonify({
                    'rate': cached_rate,
                    'cached': True,
                    'timestamp': cached_time.isoformat()
                })

        # Fetch from API
        # Alternative: Use exchangerate-api.io or other free exchange rate API
        # For now, we'll use a ticker approach with yfinance
        try:
            # Use TWD=X ticker for USD/TWD rate
            ticker = yf.Ticker('TWD=X')
            hist = ticker.history(period='1d')

            if not hist.empty:
                rate = float(hist['Close'].iloc[-1])
            else:
                # Fallback to approximate rate if API fails
                rate = 31.5  # Approximate rate as fallback

            exchange_rate_cache['USDTWD'] = (now, rate)

            return jsonify({
                'rate': round(rate, 4),
                'cached': False,
                'timestamp': now.isoformat()
            })
        except:
            # Fallback rate
            rate = 31.5
            return jsonify({
                'rate': rate,
                'cached': False,
                'fallback': True,
                'timestamp': now.isoformat()
            })

    except Exception as e:
        return jsonify({'error': str(e), 'rate': 31.5}), 500

@app.route('/api/portfolio/allocation', methods=['POST'])
def get_portfolio_allocation():
    """
    Calculate portfolio allocation by stock, market, and sector
    Body: {
        "holdings": [
            {"symbol": "AAPL", "market": "US", "value": 15000},
            {"symbol": "2330.TW", "market": "TW", "value": 500000}
        ]
    }
    """
    try:
        holdings = request.json.get('holdings', [])

        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400

        total_value = sum(h['value'] for h in holdings)

        # Calculate allocation by stock
        by_stock = []
        for holding in holdings:
            percentage = (holding['value'] / total_value) * 100 if total_value > 0 else 0
            by_stock.append({
                'symbol': holding['symbol'],
                'value': holding['value'],
                'percentage': round(percentage, 2)
            })

        # Calculate allocation by market
        market_totals = {}
        for holding in holdings:
            market = holding.get('market', 'US')
            market_totals[market] = market_totals.get(market, 0) + holding['value']

        by_market = []
        for market, value in market_totals.items():
            percentage = (value / total_value) * 100 if total_value > 0 else 0
            by_market.append({
                'market': market,
                'value': value,
                'percentage': round(percentage, 2)
            })

        return jsonify({
            'totalValue': total_value,
            'byStock': sorted(by_stock, key=lambda x: x['value'], reverse=True),
            'byMarket': sorted(by_market, key=lambda x: x['value'], reverse=True)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("Starting Stock Portfolio API Server...")
    print("Server will run on http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  GET  /api/stock/<symbol>        - Get single stock price")
    print("  POST /api/stocks/batch          - Get multiple stock prices")
    print("  GET  /api/indices               - Get major market indices")
    print("  GET  /api/history/<symbol>      - Get stock historical data")
    print("  POST /api/portfolio/history     - Get portfolio value history")
    print("  GET  /api/exchange-rate         - Get USD/TWD exchange rate")
    print("  POST /api/portfolio/allocation  - Get portfolio allocation breakdown")
    print("  GET  /health                    - Health check")
    app.run(debug=True, port=5000)
