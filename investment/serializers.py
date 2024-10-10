from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import math
from .models import TradingView, Watchlist, CurrentInvestment, Book

class TradingviewObjectiveSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    description = serializers.CharField()
    technical_rating = serializers.CharField()
    oscillators_rating = serializers.CharField()
    moving_avg_rating = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    perf_weekly = serializers.DecimalField(max_digits=10, decimal_places=2)
    perf_monthly = serializers.DecimalField(max_digits=10, decimal_places=2)
    perf_3m = serializers.DecimalField(max_digits=10, decimal_places=2)
    perf_ytd = serializers.DecimalField(max_digits=10, decimal_places=2)
    perf_6m = serializers.DecimalField(max_digits=10, decimal_places=2)
    vol_1w = serializers.DecimalField(max_digits=10, decimal_places=2)
    vol_1m = serializers.DecimalField(max_digits=10, decimal_places=2)
    on_watchlist = serializers.SerializerMethodField()
    in_portfolio = serializers.SerializerMethodField()
    asset_class = serializers.CharField()
    country = serializers.CharField()
    region = serializers.CharField()
    sub_region = serializers.CharField()
    objective = serializers.CharField()
    hedge_ccy = serializers.CharField()
    turnover_monthly = serializers.IntegerField()
    num_trades_monthly = serializers.IntegerField()
    volume_monthly = serializers.IntegerField()
    avg_trade_size_monthly = serializers.IntegerField()
    turnover_weekly = serializers.IntegerField()
    num_trades_weekly = serializers.IntegerField()
    avg_spread = serializers.IntegerField()
    avg_trade_size_weekly = serializers.IntegerField()
    trading_currency = serializers.CharField()

     # Send the primary key 'isin' to frontend as 'id'
    id = serializers.CharField(source='ticker', read_only=True)
    on_watchlist = serializers.SerializerMethodField()
    in_portfolio = serializers.SerializerMethodField()

    class Meta:
        model = TradingView
        fields = [
            'id', 'description', 'technical_rating', 'oscillators_rating',
            'moving_avg_rating', 'price', 'perf_weekly', 'perf_monthly', 'perf_3m',
            'perf_ytd', 'perf_6m', 'vol_1w', 'vol_1m', 'on_watchlist', 'asset_class',
            'country', 'region', 'sub_region', 'objective', 'hedge_ccy', 'trading_currency',
            'turnover_monthly', 'num_trades_monthly', 'volume_monthly', 'avg_trade_size_monthly',
            'turnover_weekly', 'num_trades_weekly', 'avg_spread', 'avg_trade_size_weekly',
            'in_portfolio'
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        for key, value in ret.items():
            if isinstance(value, float) and math.isnan(value):
                ret[key] = None
        return ret

    def get_on_watchlist(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'watchlist_cache'):
            return obj.ticker in request.watchlist_cache
        return False

    def get_in_portfolio(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'portfolio_cache'):
            return obj.ticker in request.portfolio_cache
        return False


class NotInManualMetaViewSerializer(serializers.ModelSerializer):
     # Fields from the TradingView model
    ticker = serializers.CharField()
    description = serializers.CharField()

    class Meta:
        model = TradingView  # You can choose either model, as they share the same primary key
        fields = [
            'ticker', 'description',
        ]


class WatchlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Watchlist
        fields = '__all__'


class CurrentInvestmentSerializer(serializers.ModelSerializer):
    qty = serializers.IntegerField(required=True)
    calculated_gbp_value = serializers.FloatField()
    pct_chg = serializers.FloatField()
    trading_currency = serializers.CharField()
    technical_rating = serializers.CharField()
    price = serializers.FloatField()
    class Meta:
        model = CurrentInvestment
        fields = ['id', 'qty', 'ticker', 'avg_px','trading_currency', 'book', 'price','calculated_gbp_value', 'pct_chg', 'technical_rating']

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
