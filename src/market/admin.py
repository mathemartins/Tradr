import zoneinfo
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from rangefilter.filters import (
    DateTimeRangeFilterBuilder,
)
from .models import Company, Quote


class QuoteInline(admin.TabularInline):
    """
    Inline display of Quote instances in the Company admin page.
    """
    model = Quote
    extra = 0  # No extra empty forms
    readonly_fields = (
        'time',
        'open_price',
        'close_price',
        'high_price',
        'low_price',
        'volume',
        'volume_weighted_average',
        'number_of_trades'
    )
    can_delete = False
    ordering = ('-time',)  # Most recent quotes first

    def get_queryset(self, request, obj=None):
        """
        Filter quotes based on the company's category.
        """
        qs = super().get_queryset(request)
        if obj:  # Check if a company object is being edited
            return qs.filter(category=obj.category)
        return qs


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Company instances.
    """
    list_display = ('name', 'ticker', 'active', 'last_updated', 'view_quotes')
    list_filter = ('active', 'timestamp', 'updated', 'category')
    search_fields = ('name', 'ticker')
    readonly_fields = ('timestamp', 'updated')
    inlines = [QuoteInline]

    def last_updated(self, obj):
        """
        Custom display for the `updated` field.
        """
        return obj.updated.strftime("%Y-%m-%d %H:%M:%S")

    last_updated.short_description = 'Last Updated'

    def view_quotes(self, obj):
        """
        Link to filtered Quote view for the company.
        """
        return format_html(
            '<a href="{}">View Quotes</a>',
            f"/admin/market/quote/?company__id__exact={obj.id}"
        )

    view_quotes.short_description = 'Quotes'


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    """
    Admin interface for managing StockQuote instances.
    """
    list_display = (
        'company',
        'company__ticker',
        'time',
        'localized_time',
        'open_price',
        'close_price',
        'high_price',
        'low_price',
        'volume',
        'number_of_trades'
    )
    list_filter = ('company__name', ('time', DateTimeRangeFilterBuilder()), 'time')
    search_fields = ('company__name', 'company__ticker', 'raw_timestamp')
    readonly_fields = (
        'time',
        'raw_timestamp',
        'localized_time',
        'open_price',
        'close_price',
        'high_price',
        'low_price',
        'volume',
        'volume_weighted_average',
        'number_of_trades'
    )
    ordering = ('-time',)

    def localized_time(self, obj):
        tz_name = "US/Eastern"
        user_tz = zoneinfo.ZoneInfo(tz_name)
        local_time = obj.time.astimezone(user_tz)
        return local_time.strftime("%b %d, %Y, %I:%M %p (%Z)")

    def get_queryset(self, request):
        tz_name = "US/Eastern"
        tz_name = "UTC"
        user_tz = zoneinfo.ZoneInfo(tz_name)
        timezone.activate(user_tz)
        return super().get_queryset(request)

    def has_add_permission(self, request):
        """
        Prevent adding new StockQuote instances manually.
        """
        return False

    def company(self, obj):
        """
        Display a link to the related Company in Quote admin.
        """
        return format_html(
            '<a href="{}">{}</a>',
            f"/admin/market/company/{obj.company.id}/change/",
            obj.company.name
        )

    company.short_description = 'Company'
