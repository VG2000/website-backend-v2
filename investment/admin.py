from django.contrib import admin
from .models import (
    Equity, Etp, Bond, MonthlyVolume, WeeklyVolume, Region, SubRegion, Country,
    ManualMeta, TradingView, Watchlist, Book, CurrentInvestment, Portfolio, Currency
)

# Register your models here.
admin.site.register(Equity)
admin.site.register(Etp)
admin.site.register(Bond)
admin.site.register(MonthlyVolume)
admin.site.register(WeeklyVolume)
admin.site.register(Region)
admin.site.register(SubRegion)
admin.site.register(Country)
admin.site.register(ManualMeta)
admin.site.register(TradingView)
admin.site.register(Watchlist)
admin.site.register(Book)
admin.site.register(CurrentInvestment)
admin.site.register(Portfolio)
admin.site.register(Currency)

