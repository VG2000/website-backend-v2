from django.db import models

# ************************LONDON STOCK EXCHANGE MODELS ************************


class Equity(models.Model):
    class Meta:
        db_table = "tblEquity"
        verbose_name_plural = "Equities"

    last_updated = models.DateTimeField(auto_now=True)
    ticker = models.CharField(max_length=255, primary_key=True)
    issuer_name = models.CharField(max_length=255)
    instrument_name = models.CharField(max_length=255)
    isin = models.CharField(max_length=12)
    mifir_identifier_code = models.CharField(max_length=255)
    icb_industry = models.CharField(max_length=255)
    icb_super_sector = models.CharField(max_length=255)
    start_date = models.DateField(null=True)
    country_of_incorporation = models.CharField(max_length=50)
    trading_currency = models.CharField(max_length=3)
    mkt_cap_mm = models.FloatField(null=True)
    lse_market = models.CharField(max_length=50)
    fca_listing_category = models.CharField(max_length=255, null=True)
    market_segment_code = models.CharField(max_length=10)
    market_sector_code = models.CharField(max_length=10)


class Bond(models.Model):

    class Meta:
        db_table = "tblBond"

    last_updated = models.DateTimeField(auto_now=True)
    ticker = models.CharField(max_length=255, primary_key=True)
    issuer_name = models.CharField(max_length=255)
    instrument_name = models.CharField(max_length=255)
    isin = models.CharField(max_length=12)
    mifir_identifier_code = models.CharField(max_length=10)
    mifir_sub_class_code = models.CharField(max_length=10)
    mifir_sub_class_name = models.CharField(max_length=255)
    start_date = models.DateField(null=True)
    maturity_date = models.DateField(null=True)
    coupon_interest_rate = models.FloatField(null=True)
    country_of_incorporation = models.CharField(max_length=50)
    trading_currency = models.CharField(max_length=3)
    lse_market = models.CharField(max_length=50)
    fca_listing_category = models.CharField(max_length=255, null=True)
    market_segment_code = models.CharField(max_length=10)
    market_sector_code = models.CharField(max_length=10)


class Etp(models.Model):

    class Meta:
        db_table = "tblEtp"

    last_updated = models.DateTimeField(auto_now=True)
    ticker = models.CharField(max_length=255, primary_key=True)
    issuer_name = models.CharField(max_length=255)
    instrument_name = models.CharField(max_length=255)
    isin = models.CharField(max_length=12)
    mifir_identifier_code = models.CharField(max_length=255)
    start_date = models.DateField()
    country_of_incorporation = models.CharField(max_length=50)
    trading_currency = models.CharField(max_length=3)
    lse_market = models.CharField(max_length=50)
    fca_listing_category = models.CharField(max_length=255, null=True)
    market_segment_code = models.CharField(max_length=10)
    market_sector_code = models.CharField(max_length=10)

    def __str__(self) -> str:
        return self.ticker


class MonthlyVolume(models.Model):

    class Meta:
        db_table = "tblMonthlyVolume"

    last_updated = models.DateTimeField(auto_now=True)
    ticker = models.CharField(max_length=255, primary_key=True)
    isin = models.CharField(max_length=12)
    gbp_turnover = models.FloatField(null=True)
    number_of_trades = models.IntegerField()
    volume = models.FloatField(null=True)
    avg_trade_size = models.FloatField(null=True)

    def __str__(self) -> str:
        return self.ticker

    def save(self, *args, **kwargs):
        # Convert blank strings to None for fields that allow null values
        for field in ['gbp_turnover', 'volume', 'avg_trade_size', 'number_of_trades']:
            value = getattr(self, field)
            if value == "":  # Check if the value is a blank string
                # Skip saving if any of the fields are blank strings
                print(f"Skipping save due to blank string in field: {field}")
                return

        super().save(*args, **kwargs)


class WeeklyVolume(models.Model):

    class Meta:
        db_table = "tblWeeklyVolume"

    last_updated = models.DateTimeField(auto_now=True)
    ticker = models.CharField(max_length=255, primary_key=True)
    isin = models.CharField(max_length=12)
    gbp_turnover = models.FloatField(null=True)
    number_of_trades = models.IntegerField()
    avg_spread = models.FloatField(null=True)
    avg_trade_size = models.FloatField(null=True)

    def __str__(self) -> str:
        return self.ticker

    def save(self, *args, **kwargs):
        # Convert blank strings to None for fields that allow null values
        for field in ['gbp_turnover', 'avg_spread', 'avg_trade_size', 'number_of_trades']:
            value = getattr(self, field)
            if value == "":  # Check if the value is a blank string
                setattr(self, field, None)  # Set the field to None instead of blank string

        super().save(*args, **kwargs)


# ************************GEOGRAPHY AND MANUAL META MODELS ************************


class Region(models.Model):

    class Meta:
        db_table = "tblRegion"

    name = models.CharField(max_length=255, primary_key=True)

    def __str__(self):
        return self.name


class SubRegion(models.Model):

    class Meta:
        db_table = "tblSubRegion"

    name = models.CharField(max_length=255, primary_key=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name


class Country(models.Model):

    class Meta:
        db_table = "tblCountry"
        verbose_name_plural = "Countries"

    alpha_2 = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=255, primary_key=True)
    subregion = models.ForeignKey(
        SubRegion, on_delete=models.CASCADE, blank=True, null=True
    )

    def __str__(self):
        return self.name


class ManualMeta(models.Model):

    class Meta:
        db_table = "tblManualMeta"

    last_updated = models.DateTimeField(auto_now=True)
    ticker = models.CharField(max_length=45, primary_key=True)
    asset_class = models.CharField(max_length=25)
    country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, blank=True, null=True
    )
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL, blank=True, default="Global", null=True
    )
    sub_region = models.ForeignKey(
        SubRegion, on_delete=models.SET_NULL, blank=True, null=True
    )
    objective = models.CharField(max_length=50)
    emerging_mkt = models.BooleanField(default=False)
    leverage_typ = models.CharField(max_length=10, null=True)
    hedge_ccy = models.CharField(max_length=5, null=True)
    single_stock = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.region and self.region.name == "Global":
            self.sub_region = None
            self.country = None

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.ticker


# ************************TRADINGVIEW MODELS ************************

class TradingView(models.Model):

    class Meta:
        db_table = "tblTradingview"

    last_updated = models.DateTimeField(auto_now=True)
    ticker = models.CharField(max_length=255, primary_key=True)
    description = models.CharField(max_length=255)
    technical_rating = models.CharField(max_length=25)
    oscillators_rating = models.CharField(max_length=25)
    moving_avg_rating = models.CharField(max_length=25)
    price = models.FloatField(null=True)
    perf_weekly = models.FloatField(null=True)
    perf_monthly = models.FloatField(null=True)
    perf_3m = models.FloatField(null=True)
    perf_ytd = models.FloatField(null=True)
    perf_6m = models.FloatField(null=True)
    vol_1w = models.FloatField(null=True)
    vol_1m = models.FloatField(null=True)

    def __str__(self) -> str:
        return self.ticker


class Watchlist(models.Model):

    class Meta:
        db_table = "tblWatchlist"

    last_updated = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=4, primary_key=True)


# NO LONGER USED - Portfolio positions taken from CurrentInvestment model =======================
class Portfolio(models.Model):

    class Meta:
        db_table = "tblPortfolio"

    last_updated = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=4, primary_key=True)


class Book(models.Model):

    class Meta:
        db_table = "tblBook"

    last_updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20, primary_key=True)


class Currency(models.Model):

    class Meta:
        db_table = "tbleCurrency"

    name = models.CharField(default='GBP', max_length=3, primary_key=True)
    gbp_value = models.FloatField(default=1)


class CurrentInvestment(models.Model):

    class Meta:
        db_table = "tblCurrentInvestment"

    id = models.AutoField(primary_key=True)
    last_updated = models.DateTimeField(auto_now=True)
    qty = models.PositiveIntegerField(null=True)
    ticker = models.ForeignKey('Etp', to_field='ticker', on_delete=models.CASCADE, db_column='ticker')
    avg_px = models.FloatField()
    current_px = models.FloatField() # NO LONGER USED - WILL FETCH FROM TRADINGVIEW
    book = models.ForeignKey('Book', to_field='name', on_delete=models.CASCADE, db_column='book')

    def __str__(self):
        return f"{self.ticker.ticker} - {self.book.name}"