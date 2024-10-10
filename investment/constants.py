from datetime import datetime


###########################################Instruments worksheet constants ################################
INSTRUMENT_SKIP_ROWS = 8  # Number of spreadsheet rows before table header row
INSTRUMENT_START_DATE = datetime(
    2020, 4, 30
)  # Date of first LSE Instrument xlsx workbook
INSTRUMENT_BASE_URL = "https://docs.londonstockexchange.com/sites/default/files/reports/Instrument%20list_"

# Instrument xlsx sheet name to database table mappings
INSTRUMENT_COLS_EQUITY = {
    "tidm": "ticker",
    "issuer name": "issuer_name",
    "instrument name": "instrument_name",
    "isin": "isin",
    "mifir identifier code": "mifir_identifier_code",
    "icb industry": "icb_industry",
    "icb super-sector name": "icb_super_sector",
    "start date": "start_date",
    "country of incorporation": "country_of_incorporation",
    "trading currency": "trading_currency",
    "security mkt cap (in £m)": "mkt_cap_mm",
    "lse market": "lse_market",
    "fca listing category": "fca_listing_category",
    "market segment code": "market_segment_code",
    "market sector code": "market_sector_code",
}

INSTRUMENT_COLS_BONDS = {
    "tidm": "ticker",
    "issuer name": "issuer_name",
    "instrument name": "instrument_name",
    "isin": "isin",
    "mifir identifier code": "mifir_identifier_code",
    "mifir sub-class code": "mifir_sub_class_code",
    "mifir sub-class name": "mifir_sub_class_name",
    "start date": "start_date",
    "maturity date": "maturity_date",
    "coupon interest rate": "coupon_interest_rate",
    "country of incorporation": "country_of_incorporation",
    "trading currency": "trading_currency",
    "lse market": "lse_market",
    "fca listing category": "fca_listing_category",
    "market segment code": "market_segment_code",
    "market sector code": "market_sector_code",
}


INSTRUMENT_COLS_ETP = {
    "tidm": "ticker",
    "issuer name": "issuer_name",
    "instrument name": "instrument_name",
    "isin": "isin",
    "mifir identifier code": "mifir_identifier_code",
    "start date": "start_date",
    "country of incorporation": "country_of_incorporation",
    "trading currency": "trading_currency",
    "lse market": "lse_market",
    "fca listing category": "fca_listing_category",
    "market segment code": "market_segment_code",
    "market sector code": "market_sector_code",
}

# Instrument dataframe dtypes mapping if not text
INSTRUMENT_DTYPES = {
    "start_date": {"dtype": "datetime64"},
    "mkt_cap_mm": {"dtype": "float64"},
    "maturity_date": {"dtype": "datetime64"},
    "coupon_interest_rate": {"dtype": "float64"},
}

# Sheet name from the LSE Instrument sheet must match the column mapping for insertion to db. Check spellings!
INSTRUMENT_SHEET_MAP = {
    "1.1 Shares": INSTRUMENT_COLS_EQUITY,
    "2.1 Bonds": INSTRUMENT_COLS_BONDS,
    "1.3 ETFs": INSTRUMENT_COLS_ETP,
    "2.2 ETCs": INSTRUMENT_COLS_ETP,
    "2.3 ETNs": INSTRUMENT_COLS_ETP,
}

# Table names for the db will be matched to  the LSE Instrument sheets keys. Also sets if_exists property when saving to db
# "concat" is True for ETFs except for the last iteration when it is sent to the model o
INSTRUMENT_MODEL_MAP = {
    "1.1 Shares": {"model": 'Equity'},
    "2.1 Bonds": {"model": 'Bond'},
    "1.3 ETFs": {"model": 'Etp'},
    "2.2 ETCs": {"model":'Etp'},
    "2.3 ETNs": {"model": 'Etp'},
}


########################################### Monthly volume worksheet constants ################################
MONTHLY_EQUITY_SHEET = "Trading Summary Factsheet"
MONTHLY_ETP_SHEET = "ETFs & ETPs Trading by Security"
MONTHLY_TABLE = "london_stock_exchange_monthlyvolume"
MONTHLY_EQUITY_VOLUME_SKIP_ROWS = 6
MONTHLY_ETP_VOLUME_SKIP_ROWS = 6
MONTHLY_EQUITY_BASE_URL = f"https://docs.londonstockexchange.com/sites/default/files/reports/Trading%20statistics%20"
MONTHLY_ETP_BASE_URL = url = (
    f"https://docs.londonstockexchange.com/sites/default/files/reports/ETF%20and%20ETP%20Monthly%20trading"
    f"%20data%20by%20security%20"
)

MONTHLY_EQUITY_VOLUME_MAP = {
    "tidm": "ticker",
    "isin": "isin",
    "value traded (£)": "gbp_turnover",
    "trades": "number_of_trades",
    "volume": "volume",
}

MONTHLY_ETP_VOLUME_MAP = {
    "tidm": "ticker",
    "isin": "isin",
    "value of trades (£).4": "gbp_turnover",
    "number of trades.4": "number_of_trades",
    "volume": "volume",
}

# Monthly Volume dataframe dtypes mapping if not text
MONTHLY_DTYPES = {
    "gbp_turnover": {"dtype": "float64"},
    "number_of_trades": {"dtype": "integer"},
    "volume": {"dtype": "float64"},
    "avg_trade_size": {"dtype": "float64"},
}

########################################### Monthly volume worksheet constants ################################
# Weekly volumes
WEEKLY_ETP_VOLUME_SKIP_ROWS = 5
WEEKLY_TABLE = "london_stock_exchange_weeklyvolume"
WEEKLY_BASE_URL = (
    f"https://docs.londonstockexchange.com/sites/default/files/reports/ETF%20and%20ETP%20weekly"
    f"%20statistics%20-%20week%20ending%20"
)

WEEKLY_ETP_VOLUME_SHEET = "ETFs"

WEEKLY_ETP_VOLUME_MAP = {
    "tidm": "ticker",
    "isin": "isin",
    "number of trades": "number_of_trades",
    "gbp turnover": "gbp_turnover",
    "average trade size": "avg_trade_size",
    "time weighted spread (bps)": "avg_spread",
}

# Weeky Volume dataframe dtypes mapping if not text
WEEKLY_DTYPES = {
    "gbp_turnover": {"dtype": "float64"},
    "number_of_trades": {"dtype": "integer"},
    "avg_trade_size": {"dtype": "float64"},
    "avg_spread": {"dtype": "float64"},
}

########################################### Tradingview constants ################################
# TradingView download path - Should be available on iCloud drive
####THIS IS NOT GOING TO WORK - USE S3 BUCKET?#####
TV_DATA_DIRECTORY_PATH = '/Users/vincentgomez/Documents/TradingView'
# Database table name
TRADINGVIEW_TABLE = "tradingview"
# Tradingview column map
TRADINGVIEW_COLS = {
                'Ticker': 'ticker',
                'Description': 'description',
                'Technical Rating': 'technical_rating',
                'Oscillators Rating': 'oscillators_rating',
                'Moving Averages Rating': 'moving_avg_rating',
                'Price': 'price',
                'Weekly Performance': 'perf_weekly',
                'Monthly Performance': 'perf_monthly',
                '3-Month Performance': 'perf_3m',
                'YTD Performance': 'perf_ytd',
                '6-Month Performance': 'perf_6m',
                'Volatility Month': 'vol_1w',
                'Volatility Week': 'vol_1m'
            }

# Weeky Volume dataframe dtypes mapping if not text
TRADINGVIEW_DTYPES = {
    "price": {"dtype": "float64"},
    "perf_weekly": {"dtype": "float64"},
    "perf_monthly": {"dtype": "float64"},
    "perf_3m": {"dtype": "float64"},
    "perf_ytd": {"dtype": "float64"},
    "perf_6m": {"dtype": "float64"},
    "vol_1w": {"dtype": "float64"},
    "vol_1m": {"dtype": "float64"},
}