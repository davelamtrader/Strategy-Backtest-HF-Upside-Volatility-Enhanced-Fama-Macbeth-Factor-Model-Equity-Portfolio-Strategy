#海通证券-选股因子系列研究（二十五）：高频因子之已实现波动分解
import os
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import quantstats as qs
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

# --- 1. Data Preparation ---

def get_eod_prices(ticker, start_date, end_date, api_key):
    """Fetches daily EOD prices to calculate next month's returns."""
    url = f"https://eodhd.com/api/eod/{ticker}.US?from={start_date}&to={end_date}&api_token={api_key}&period=d&fmt=json"
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        return df['adjusted_close'].rename(ticker)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching EOD data for {ticker}: {e}")
        return None

def fetch_intraday_data(ticker, date, interval, api_key):
    """
    Fetches 1-minute or 5-minute intraday data for a specific ticker on a given date from EODHD.
    Note: EODHD provides 1-min data for the last few months. Historical access might be limited.
    """
    unix_from = int(datetime.strptime(f"{date} 09:30:00", "%Y-%m-%d %H:%M:%S").timestamp())
    unix_to = int(datetime.strptime(f"{date} 16:00:00", "%Y-%m-%d %H:%M:%S").timestamp())
    
    url = f"https://eodhd.com/api/intraday/{ticker}.US?api_token={api_key}&interval={interval}&from={unix_from}&to={unix_to}&fmt=json"
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch intraday for {ticker} on {date}: {e}")
        return pd.DataFrame()

# --- 2. Signal Generation ---

def calculate_upside_volatility_factor(df_intraday):
    """
    Calculates the 'Upside Volatility Proportion' factor from intraday data.
    This logic is based on the report's concept of splitting volatility into
    upside and downside components.
    """
    if df_intraday.empty or len(df_intraday) < 2:
        return np.nan

    # Calculate high-frequency returns
    df_intraday['returns'] = df_intraday['close'].pct_change()
    
    # Total realized volatility (standard deviation of returns)
    total_vol = df_intraday['returns'].std()
    
    # Separate returns into upside and downside
    upside_returns = df_intraday['returns'][df_intraday['returns'] > 0]
    
    if len(upside_returns) < 2:
        return np.nan # Not enough data to calculate upside volatility
        
    # Calculate upside volatility
    upside_vol = upside_returns.std()
    
    # The factor is the proportion of upside volatility to total volatility.
    # A higher value indicates more of the volatility comes from upward price swings. 
    if total_vol == 0:
        return np.nan
        
    upside_vol_proportion = upside_vol / total_vol
    
    return upside_vol_proportion

def get_monthly_factor_value(ticker, year, month, interval, api_key):
    """
    Calculates the average factor value for a ticker over a given month.
    """
    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1) - timedelta(days=1)
    
    monthly_factor_values = []
    
    # Iterate through all trading days in the month
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5: # Monday to Friday
            df_intraday = fetch_intraday_data(ticker, current_date.strftime('%Y-%m-%d'), interval, api_key)
            if not df_intraday.empty:
                daily_factor = calculate_upside_volatility_factor(df_intraday)
                if not np.isnan(daily_factor):
                    monthly_factor_values.append(daily_factor)
        current_date += timedelta(days=1)

    if not monthly_factor_values:
        return np.nan
        
    return np.mean(monthly_factor_values)


# --- 3. Backtest Logic and Trading Rules ---
# The logic follows the findings of the report:
# - Rebalance monthly 
# - Go long on stocks with low factor values (low upside volatility proportion)
# - Go short on stocks with high factor values (high upside volatility proportion)

def run_backtest(tickers, start_year, end_year, interval='1m'):
    """
    Conducts the backtest from the specified start to end year.
    """
    all_monthly_returns = []
    
    # --- Fetch all EOD data at once for performance ---
    start_dt_eod = f"{start_year}-01-01"
    end_dt_eod = f"{end_year}-06-30"
    all_eod_data = {}
    print("Fetching all EOD data...")
    for ticker in tqdm(tickers):
        eod_df = get_eod_prices(ticker, start_dt_eod, end_dt_eod, EODHD_API_KEY)
        if eod_df is not None:
            all_eod_data[ticker] = eod_df
    
    valid_tickers = list(all_eod_data.keys())

    # --- Main Backtest Loop ---
    # The report rebalances monthly.
    current_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 7, 1)

    while current_date < end_date:
        rebalance_month = current_date.month
        rebalance_year = current_date.year
        
        print(f"\nProcessing rebalance for {rebalance_year}-{rebalance_month:02d}...")
        
        # --- Calculate factor for all tickers for the current month ---
        factor_values = {}
        for ticker in tqdm(valid_tickers, desc="Calculating factor"):
            factor = get_monthly_factor_value(ticker, rebalance_year, rebalance_month, interval, EODHD_API_KEY)
            if not np.isnan(factor):
                factor_values[ticker] = factor
        
        if len(factor_values) < 5: # Need enough stocks to form quintiles
            print("Not enough data to form portfolio. Skipping month.")
            current_date += relativedelta(months=1)
            continue

        factor_series = pd.Series(factor_values).dropna()
        
        # --- Form Long/Short Portfolios based on factor quintiles ---
        # The report finds that high factor values predict poor returns. 
        # So we short the top quintile and long the bottom quintile.
        quintiles = pd.qcut(factor_series, 5, labels=False, duplicates='drop')
        
        long_portfolio = factor_series[quintiles == 0].index.tolist()
        short_portfolio = factor_series[quintiles == 4].index.tolist()
        
        if not long_portfolio or not short_portfolio:
            print("Could not form long/short portfolios. Skipping month.")
            current_date += relativedelta(months=1)
            continue
            
        print(f"Long portfolio: {long_portfolio}")
        print(f"Short portfolio: {short_portfolio}")

        # --- Calculate portfolio return for the NEXT month ---
        # The factor is calculated at month-end to predict the next month's return. 
        trade_start_date = current_date + relativedelta(months=1)
        trade_end_date = trade_start_date + relativedelta(months=1) - timedelta(days=1)
        
        long_returns = []
        for ticker in long_portfolio:
            try:
                eod = all_eod_data[ticker]
                start_price = eod.loc[:trade_start_date.strftime('%Y-%m-%d')].iloc[-1]
                end_price = eod.loc[:trade_end_date.strftime('%Y-%m-%d')].iloc[-1]
                long_returns.append((end_price / start_price) - 1)
            except (KeyError, IndexError):
                continue

        short_returns = []
        for ticker in short_portfolio:
            try:
                eod = all_eod_data[ticker]
                start_price = eod.loc[:trade_start_date.strftime('%Y-%m-%d')].iloc[-1]
                end_price = eod.loc[:trade_end_date.strftime('%Y-%m-%d')].iloc[-1]
                # For a short position, the return is -(p_end / p_start - 1)
                short_returns.append(-((end_price / start_price) - 1))
            except (KeyError, IndexError):
                continue
        
        # --- Calculate monthly return for the strategy ---
        # The report mentions transaction costs of 0.15% (15bps) per side.
        transaction_costs = 0.0015 * 2 # Long and short side
        
        avg_long_return = np.mean(long_returns) if long_returns else 0
        avg_short_return = np.mean(short_returns) if short_returns else 0
        
        # Equal-weighted long-short portfolio
        monthly_net_return = (avg_long_return + avg_short_return) / 2 - transaction_costs
        
        all_monthly_returns.append({
            'date': trade_start_date,
            'return': monthly_net_return
        })
        
        # Move to the next month for rebalancing
        current_date += relativedelta(months=1)
        
    return pd.DataFrame(all_monthly_returns).set_index('date')['return']


# --- 4. Conduct Backtest & 5. Evaluate Performance ---

if __name__ == '__main__':

    EODHD_API_KEY = os.getenv('EODHD_API_KEY', 'YOUR_API_KEY') 
    # For demonstration purposes, we will use a smaller, fixed list of tickers.
    # In a real scenario, you would dynamically fetch the Nasdaq 100 constituents.
    NASDAQ_100_SAMPLE = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'JPM', 'JNJ']

    # Validate API Key
    if EODHD_API_KEY == 'YOUR_API_KEY':
        print("!!! PLEASE REPLACE 'YOUR_API_KEY' with your EODHD API key.")
    else:
        # Step 4: Conduct the backtest for the specified date range and interval
        print("Starting backtest for Upside Volatility Proportion Factor...")
        strategy_returns = run_backtest(
            tickers=NASDAQ_100_SAMPLE,
            start_year=2020,
            end_year=2025,
            interval='1m'
        )

        if not strategy_returns.empty:
            print("\nBacktest complete. Generating performance report...")
            
            qs.extend_pandas()
            # Use a benchmark, e.g., QQQ for Nasdaq 100
            benchmark = qs.utils.download_returns('QQQ')
            
            # Generate and save the full HTML report
            output_filename = 'high_freq_vol_strategy_report.html'
            qs.reports.html(strategy_returns, benchmark=benchmark, output=output_filename,
                            title='High-Frequency Upside Volatility Strategy')
            
            print(f"\nPerformance evaluation complete. Report saved as '{output_filename}'.")
            
            # Display key stats
            qs.stats.display(strategy_returns)
        else:
            print("\nBacktest did not generate any returns. Check data fetching and logic.")

