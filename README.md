# Strategy-Backtest-HF-Upside-Volatility-Enhanced-Fama-Macbeth-Factor-Model-Equity-Portfolio-Strategy

## Overview

This repository presents a trading strategy that decomposes high-frequency volatility to identify trading signals. The strategy leverages the concept of separating total realized volatility into upside and downside components, and aims to capture market inefficiencies by analyzing the proportion of upside volatility.

## Strategy Components

### 1. Data Acquisition

-   **Data Source:**  The strategy uses intraday and EOD data from EODHD API  .
-   **EOD Data Fetching:**  The code includes a function  get_eod_prices()  to fetch daily EOD price data, which is used for calculating next month's returns  .
-   **Intraday Data Fetching:**  The  fetch_intraday_data()  function retrieves 1-minute or 5-minute intraday data for a specific ticker on a given date from EODHD  . Note that historical intraday data access might be limited  .

### 2. Signal Generation: Upside Volatility Proportion

-   **Upside Volatility Calculation:**  The  calculate_upside_volatility_factor()  function calculates the "Upside Volatility Proportion" factor from intraday data  . This factor represents the ratio of upside volatility to total realized volatility  .
-   **Factor Calculation:**  The function first calculates high-frequency returns from the intraday 'close' prices  . Then, it calculates the total realized volatility and separates returns into upside returns  .
-   **Upside Volatility Proportion:**  The strategy computes the proportion of upside volatility to total volatility, which is the key signal  . A higher value suggests that the volatility comes more from upward price swings  .
-   **Monthly Factor Value:**  The  get_monthly_factor_value()  function calculates the average factor value for a ticker over a given month by iterating through trading days  .

### 3. Backtest Logic

-   **Backtest Function:**  The  run_backtest()  function conducts the backtest for a specified period  .
-   **Rebalancing:**  The backtest rebalances monthly  .
-   **Portfolio Construction:**  The code forms long/short portfolios based on the factor quintiles  . The report suggests going long on stocks with low factor values and short on stocks with high factor values  .
-   **Monthly Returns Calculation:**  The code calculates the monthly return for the strategy, considering transaction costs  .

### 4. Performance Evaluation

-   **Performance Reporting:**  The strategy generates a performance report using  quantstats  . This report includes key statistics and performance charts  .

## Key Findings (Based on Report)

-   **High-Frequency Volatility Decomposition:**  The research decomposes high-frequency volatility to extract effective trading signals  .
-   **"Upside Volatility Proportion":**  The "上行波動佔比" (Upside Volatility Proportion) factor demonstrates good performance in the backtests  .
-   **Factor Performance:**  The research found that the upside volatility proportion factor has a good selection effect in different data frequencies  .

## Code Structure

The codebase is organized into the following functions:

-   get_eod_prices(): Fetches EOD price data  .
-   fetch_intraday_data(): Fetches intraday data  .
-   calculate_upside_volatility_factor(): Calculates the upside volatility proportion  .
-   get_monthly_factor_value(): Calculates the average factor value for a month  .
-   run_backtest(): Runs the backtest  .
-   The main section of the code handles API key validation, backtest execution and performance report generation  .

## Further Enhancements

-   **Parameter Optimization:**  Optimize parameters such as the data frequency (1-minute, 5-minute, 10-minute) and the lookback period for volatility calculation  .
-   **Market Regime Analysis:**  Explore the performance of the strategy across different market regimes (bull, bear, sideways)  .
