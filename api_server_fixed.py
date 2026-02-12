"""
Stock Portfolio API Server - Fixed Version
Uses yfinance with better error handling and rate limiting
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import yfinance as yf
import os
from datetime import datetime, timedelta
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re

app = Flask(__name__)
CORS(app)

# Cache for reducing API calls
price_cache = {}
exchange_rate_cache = {}
news_cache = {}
CACHE_DURATION = 60  # seconds
EXCHANGE_RATE_CACHE_DURATION = 3600  # 1 hour for exchange rates
NEWS_CACHE_DURATION = 1800  # 30 minutes for news

# Rate limiting
last_request_time = {}
MIN_REQUEST_INTERVAL = 0.5  # 500ms between requests to same symbol

def get_cached_or_fetch(symbol, fetch_func):
    """Get data from cache or fetch new data with rate limiting"""
    now = datetime.now()

    # Check cache first
    if symbol in price_cache:
        cached_time, cached_data = price_cache[symbol]
        if (now - cached_time).seconds < CACHE_DURATION:
            return cached_data

    # Rate limiting
    if symbol in last_request_time:
        time_since_last = (now - last_request_time[symbol]).total_seconds()
        if time_since_last < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - time_since_last)

    # Fetch new data
    data = fetch_func(symbol)
    price_cache[symbol] = (now, data)
    last_request_time[symbol] = datetime.now()

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

            # Use history instead of info to avoid rate limits
            hist = ticker.history(period='5d')  # Get more days for reliability

            if hist.empty:
                return {'error': 'No data available for ' + sym}

            current_price = hist['Close'].iloc[-1]

            # Calculate change
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100
            else:
                change = 0
                change_percent = 0

            # Try to get name (with error handling)
            name = sym
            try:
                # Use fast_info instead of info
                fast_info = ticker.fast_info
                name = fast_info.get('longName', sym)
            except:
                # If fast_info fails, just use symbol
                name = sym

            return {
                'symbol': sym,
                'price': round(float(current_price), 2),
                'change': round(float(change), 2),
                'changePercent': round(float(change_percent), 2),
                'name': name,
                'timestamp': datetime.now().isoformat()
            }

        data = get_cached_or_fetch(symbol, fetch_stock)
        return jsonify(data)

    except Exception as e:
        return jsonify({
            'error': str(e),
            'symbol': symbol,
            'price': 0,
            'change': 0,
            'changePercent': 0,
            'name': symbol
        }), 200  # Return 200 with error data instead of 500

@app.route('/api/stocks/batch', methods=['POST'])
def get_batch_stocks():
    """
    Get multiple stock prices in one request - OPTIMIZED VERSION
    Uses yf.Tickers() for batch fetching (5-10x faster)
    Body: {"symbols": ["AAPL", "2330.TW", "TSLA"]}
    """
    try:
        symbols = request.json.get('symbols', [])
        if not symbols:
            return jsonify({})

        results = {}
        now = datetime.now()

        # Separate cached and non-cached symbols
        uncached_symbols = []
        for symbol in symbols:
            if symbol in price_cache:
                cached_time, cached_data = price_cache[symbol]
                if (now - cached_time).seconds < CACHE_DURATION:
                    results[symbol] = cached_data
                else:
                    uncached_symbols.append(symbol)
            else:
                uncached_symbols.append(symbol)

        # Batch fetch uncached symbols using yf.Tickers()
        if uncached_symbols:
            try:
                # Create Tickers object with space-separated symbols
                tickers = yf.Tickers(' '.join(uncached_symbols))

                # Fetch history for all tickers at once
                hist_data = tickers.history(period='5d')

                # Process each symbol
                for symbol in uncached_symbols:
                    try:
                        # Extract data for this symbol
                        if symbol in hist_data.columns.get_level_values(1):
                            symbol_data = hist_data.xs(symbol, level=1, axis=1)

                            if not symbol_data.empty and 'Close' in symbol_data.columns:
                                current_price = symbol_data['Close'].iloc[-1]

                                # Calculate change
                                if len(symbol_data) >= 2:
                                    prev_close = symbol_data['Close'].iloc[-2]
                                    change = current_price - prev_close
                                    change_percent = (change / prev_close) * 100
                                else:
                                    change = 0
                                    change_percent = 0

                                data = {
                                    'price': round(float(current_price), 2),
                                    'change': round(float(change), 2),
                                    'changePercent': round(float(change_percent), 2)
                                }

                                # Cache the result
                                price_cache[symbol] = (now, data)
                                results[symbol] = data
                            else:
                                results[symbol] = {'error': 'No data available'}
                        else:
                            results[symbol] = {'error': 'Symbol not found'}

                    except Exception as e:
                        print(f"Error processing {symbol}: {e}")
                        results[symbol] = {'error': str(e)}

            except Exception as e:
                print(f"Batch fetch error: {e}")
                # Fallback to individual requests if batch fails
                for symbol in uncached_symbols:
                    try:
                        ticker = yf.Ticker(symbol)
                        hist = ticker.history(period='5d')

                        if not hist.empty:
                            current_price = hist['Close'].iloc[-1]

                            if len(hist) >= 2:
                                prev_close = hist['Close'].iloc[-2]
                                change = current_price - prev_close
                                change_percent = (change / prev_close) * 100
                            else:
                                change = 0
                                change_percent = 0

                            data = {
                                'price': round(float(current_price), 2),
                                'change': round(float(change), 2),
                                'changePercent': round(float(change_percent), 2)
                            }
                            price_cache[symbol] = (now, data)
                            results[symbol] = data
                        else:
                            results[symbol] = {'error': 'No data available'}
                    except Exception as inner_e:
                        results[symbol] = {'error': str(inner_e)}

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/indices', methods=['GET'])
def get_major_indices():
    """Get major market indices - batch optimized with yf.Tickers()"""
    try:
        indices = {
            'TWII': '^TWII',      # Taiwan Weighted Index
            'SPX': '^GSPC',       # S&P 500
            'NASDAQ': '^IXIC',    # Nasdaq
            'DJI': '^DJI'         # Dow Jones
        }

        results = {}
        now = datetime.now()

        # Check cache first, collect uncached symbols
        uncached = {}
        for name, symbol in indices.items():
            if symbol in price_cache:
                cached_time, cached_data = price_cache[symbol]
                if (now - cached_time).seconds < CACHE_DURATION:
                    results[name] = cached_data
                    continue
            uncached[name] = symbol

        # Batch fetch uncached indices using yf.Tickers()
        if uncached:
            try:
                symbols_str = ' '.join(uncached.values())
                tickers = yf.Tickers(symbols_str)
                hist_data = tickers.history(period='5d')

                for name, symbol in uncached.items():
                    try:
                        if symbol in hist_data.columns.get_level_values(1):
                            symbol_data = hist_data.xs(symbol, level=1, axis=1)

                            if not symbol_data.empty and 'Close' in symbol_data.columns:
                                current_value = symbol_data['Close'].iloc[-1]

                                if len(symbol_data) >= 2:
                                    prev_close = symbol_data['Close'].iloc[-2]
                                    change = current_value - prev_close
                                    change_percent = (change / prev_close) * 100
                                else:
                                    change = 0
                                    change_percent = 0

                                data = {
                                    'value': round(float(current_value), 2),
                                    'change': round(float(change), 2),
                                    'changePercent': round(float(change_percent), 2)
                                }
                                price_cache[symbol] = (now, data)
                                results[name] = data
                            else:
                                results[name] = {'error': 'No data', 'value': 0, 'change': 0, 'changePercent': 0}
                        else:
                            results[name] = {'error': 'Symbol not found', 'value': 0, 'change': 0, 'changePercent': 0}
                    except Exception as e:
                        print(f"Error processing index {name} ({symbol}): {e}")
                        results[name] = {'error': str(e), 'value': 0, 'change': 0, 'changePercent': 0}

            except Exception as e:
                print(f"Batch indices fetch error, falling back to individual: {e}")
                # Fallback to individual requests
                for name, symbol in uncached.items():
                    try:
                        ticker = yf.Ticker(symbol)
                        hist = ticker.history(period='5d')

                        if not hist.empty:
                            current_value = hist['Close'].iloc[-1]
                            if len(hist) >= 2:
                                prev_close = hist['Close'].iloc[-2]
                                change = current_value - prev_close
                                change_percent = (change / prev_close) * 100
                            else:
                                change = 0
                                change_percent = 0

                            data = {
                                'value': round(float(current_value), 2),
                                'change': round(float(change), 2),
                                'changePercent': round(float(change_percent), 2)
                            }
                            price_cache[symbol] = (now, data)
                            results[name] = data
                        else:
                            results[name] = {'error': 'No data', 'value': 0, 'change': 0, 'changePercent': 0}

                        time.sleep(0.3)
                    except Exception as inner_e:
                        results[name] = {'error': str(inner_e), 'value': 0, 'change': 0, 'changePercent': 0}

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/<symbol>', methods=['GET'])
def get_stock_history(symbol):
    """
    Get historical stock data for charts
    Query params: period (1mo, 3mo, 6mo, 1y, 2y)
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
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)

                if not hist.empty:
                    all_history[symbol] = hist

                # Small delay between requests
                time.sleep(0.2)
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                continue

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
            tw_value = 0
            tw_cost = 0
            us_value = 0
            us_cost = 0

            for holding in holdings:
                symbol = holding['symbol']
                shares = holding['shares']
                avg_cost = holding['avgCost']
                market = holding.get('market', 'TW' if '.TW' in symbol else 'US')

                if symbol in all_history:
                    hist = all_history[symbol]
                    date_data = hist[hist.index.strftime('%Y-%m-%d') == date_str]

                    if not date_data.empty:
                        close_price = float(date_data['Close'].iloc[0])
                        value = close_price * shares
                        cost = avg_cost * shares

                        total_value += value
                        total_cost += cost

                        # 分別記錄台股和美股
                        if market == 'TW':
                            tw_value += value
                            tw_cost += cost
                        else:
                            us_value += value
                            us_cost += cost

            if total_value > 0:
                pnl = total_value - total_cost
                pnl_percent = (pnl / total_cost) * 100

                portfolio_history.append({
                    'date': date_str,
                    'value': round(total_value, 2),
                    'cost': round(total_cost, 2),
                    'twValue': round(tw_value, 2),
                    'twCost': round(tw_cost, 2),
                    'usValue': round(us_value, 2),
                    'usCost': round(us_cost, 2),
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

        # Try multiple sources for exchange rate
        rate = None

        # Method 1: Try TWD=X
        try:
            ticker = yf.Ticker('TWD=X')
            hist = ticker.history(period='5d')

            if not hist.empty:
                rate = float(hist['Close'].iloc[-1])
        except:
            pass

        # Method 2: If failed, try USDTWD=X
        if rate is None or rate == 0:
            try:
                ticker = yf.Ticker('USDTWD=X')
                hist = ticker.history(period='5d')

                if not hist.empty:
                    rate = float(hist['Close'].iloc[-1])
            except:
                pass

        # Fallback rate if all methods fail
        if rate is None or rate == 0:
            rate = 31.5

        exchange_rate_cache['USDTWD'] = (now, rate)

        return jsonify({
            'rate': round(rate, 4),
            'cached': False,
            'timestamp': now.isoformat()
        })

    except Exception as e:
        # Always return a valid rate even on error
        return jsonify({
            'error': str(e),
            'rate': 31.5,
            'fallback': True
        }), 200

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

@app.route('/api/news/<symbol>', methods=['GET'])
def get_stock_news(symbol):
    """
    Get news for a specific stock
    For US stocks: uses yfinance news
    For TW stocks: uses Google News RSS
    Query params: limit (default 5)
    """
    try:
        limit = int(request.args.get('limit', 5))
        now = datetime.now()

        # Check cache first
        cache_key = f"news_{symbol}"
        if cache_key in news_cache:
            cached_time, cached_data = news_cache[cache_key]
            if (now - cached_time).seconds < NEWS_CACHE_DURATION:
                return jsonify({
                    'symbol': symbol,
                    'news': cached_data[:limit],
                    'cached': True,
                    'timestamp': cached_time.isoformat()
                })

        news_items = []

        # Check if Taiwan stock
        is_tw_stock = '.TW' in symbol.upper() or '.TWO' in symbol.upper()

        if is_tw_stock:
            # Use Google News RSS for Taiwan stocks
            news_items = fetch_google_news(symbol, limit)
        else:
            # Use yfinance for US stocks
            news_items = fetch_yfinance_news(symbol, limit)

        # Cache the results
        news_cache[cache_key] = (now, news_items)

        return jsonify({
            'symbol': symbol,
            'news': news_items[:limit],
            'cached': False,
            'timestamp': now.isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'symbol': symbol,
            'news': []
        }), 200


def fetch_yfinance_news(symbol, limit=5):
    """Fetch news using yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news

        if not raw_news:
            return []

        news_items = []
        for item in raw_news[:limit]:
            # Handle new yfinance news format (nested under 'content')
            content = item.get('content', item)  # Fallback to item if no 'content' key

            # Extract title
            title = content.get('title', item.get('title', ''))

            # Extract link - try multiple possible locations
            link = ''
            if 'canonicalUrl' in content and content['canonicalUrl']:
                link = content['canonicalUrl'].get('url', '')
            elif 'clickThroughUrl' in content and content['clickThroughUrl']:
                link = content['clickThroughUrl'].get('url', '')
            elif 'link' in item:
                link = item.get('link', '')

            # Extract source/publisher
            source = ''
            if 'provider' in content and content['provider']:
                source = content['provider'].get('displayName', '')
            elif 'publisher' in item:
                source = item.get('publisher', '')

            # Extract publish time
            pub_time = None
            time_ago = ''
            pub_date_str = content.get('pubDate', item.get('pubDate', ''))

            if pub_date_str:
                try:
                    # Parse ISO format date string
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    # Convert to local time (remove timezone info for comparison)
                    pub_date = pub_date.replace(tzinfo=None)
                    time_ago = get_time_ago(pub_date)
                    pub_time = pub_date
                except:
                    pass

            # Fallback to old format timestamp
            if not pub_time and item.get('providerPublishTime'):
                try:
                    pub_date = datetime.fromtimestamp(item.get('providerPublishTime'))
                    time_ago = get_time_ago(pub_date)
                    pub_time = pub_date
                except:
                    pass

            # Extract thumbnail
            thumbnail = ''
            thumb_data = content.get('thumbnail', item.get('thumbnail'))
            if thumb_data and 'resolutions' in thumb_data and thumb_data['resolutions']:
                thumbnail = thumb_data['resolutions'][0].get('url', '')

            news_items.append({
                'title': title,
                'link': link,
                'source': source,
                'publishedAt': pub_time.isoformat() if pub_time else '',
                'timeAgo': time_ago,
                'thumbnail': thumbnail
            })

        return news_items

    except Exception as e:
        print(f"Error fetching yfinance news for {symbol}: {e}")
        return []


def fetch_google_news(symbol, limit=5):
    """Fetch news from Google News RSS for Taiwan stocks"""
    try:
        # Extract stock number from symbol (e.g., 2330.TW -> 2330)
        stock_number = symbol.replace('.TW', '').replace('.TWO', '')

        # Search query - try to get company name or use stock number
        search_query = f"{stock_number} 股票"

        # Google News RSS URL
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

        # Create request with headers
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Fetch RSS feed
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read().decode('utf-8')

        # Parse XML
        root = ET.fromstring(xml_data)

        news_items = []
        items = root.findall('.//item')

        for item in items[:limit]:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            source = item.find('source')

            # Parse publish date
            time_ago = ''
            pub_datetime = None
            if pub_date is not None and pub_date.text:
                try:
                    # Parse RFC 2822 date format
                    pub_datetime = datetime.strptime(
                        pub_date.text,
                        '%a, %d %b %Y %H:%M:%S %Z'
                    )
                    time_ago = get_time_ago(pub_datetime)
                except:
                    try:
                        # Try alternative format
                        pub_datetime = datetime.strptime(
                            pub_date.text[:25],
                            '%a, %d %b %Y %H:%M:%S'
                        )
                        time_ago = get_time_ago(pub_datetime)
                    except:
                        pass

            news_items.append({
                'title': title.text if title is not None else '',
                'link': link.text if link is not None else '',
                'source': source.text if source is not None else 'Google News',
                'publishedAt': pub_datetime.isoformat() if pub_datetime else '',
                'timeAgo': time_ago,
                'thumbnail': ''
            })

        return news_items

    except Exception as e:
        print(f"Error fetching Google News for {symbol}: {e}")
        return []


def get_time_ago(dt):
    """Convert datetime to relative time string"""
    now = datetime.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return '剛剛'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes} 分鐘前'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} 小時前'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} 天前'
    else:
        return dt.strftime('%m/%d')


@app.route('/api/news/batch', methods=['POST'])
def get_batch_news():
    """
    Get news for multiple stocks
    Body: {"symbols": ["AAPL", "2330.TW"], "limit": 3}
    """
    try:
        symbols = request.json.get('symbols', [])
        limit = request.json.get('limit', 3)

        if not symbols:
            return jsonify({})

        results = {}
        now = datetime.now()

        for symbol in symbols:
            cache_key = f"news_{symbol}"

            # Check cache
            if cache_key in news_cache:
                cached_time, cached_data = news_cache[cache_key]
                if (now - cached_time).seconds < NEWS_CACHE_DURATION:
                    results[symbol] = cached_data[:limit]
                    continue

            # Fetch news
            is_tw_stock = '.TW' in symbol.upper() or '.TWO' in symbol.upper()

            if is_tw_stock:
                news_items = fetch_google_news(symbol, limit)
            else:
                news_items = fetch_yfinance_news(symbol, limit)

            # Cache and add to results
            news_cache[cache_key] = (now, news_items)
            results[symbol] = news_items[:limit]

            # Small delay between requests
            time.sleep(0.3)

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'cache_size': len(price_cache),
        'news_cache_size': len(news_cache)
    })

@app.route('/', methods=['GET'])
def serve_index():
    """Serve the main HTML page"""
    html_path = os.path.join(os.path.dirname(__file__), 'stock-portfolio-optimized.html')
    return send_file(html_path)

if __name__ == '__main__':
    print("Starting Stock Portfolio API Server (Fixed Version)...")
    print("Server will run on http://0.0.0.0:5000")
    print("Accessible from network devices")
    print("\nFeatures:")
    print("  - Better rate limiting (500ms between requests)")
    print("  - 5-day history for more reliable data")
    print("  - Graceful error handling")
    print("  - Cache duration: 60 seconds")
    print("\nAvailable endpoints:")
    print("  GET  /api/stock/<symbol>        - Get single stock price")
    print("  POST /api/stocks/batch          - Get multiple stock prices")
    print("  GET  /api/indices               - Get major market indices")
    print("  GET  /api/history/<symbol>      - Get stock historical data")
    print("  POST /api/portfolio/history     - Get portfolio value history")
    print("  GET  /api/exchange-rate         - Get USD/TWD exchange rate")
    print("  POST /api/portfolio/allocation  - Get portfolio allocation breakdown")
    print("  GET  /api/news/<symbol>         - Get stock news (US: yfinance, TW: Google News)")
    print("  POST /api/news/batch            - Get news for multiple stocks")
    print("  GET  /health                    - Health check")
    print("\n" + "="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
