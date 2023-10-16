import yfinance as yf

symbols = ["TLSA", "AAPL", "MSFT", "NVDA", "META"]

for symbol in symbols:
	stock_prices = yf.download(tickers=symbol, period="5d", interval="1m")
	stock_prices.to_csv(f"2023-10-15-{symbol}.csv")
