from django.db.models import (
    Avg,
    F,
    RowRange,
    Window,
    Max,
    Min,
    ExpressionWrapper,
    DecimalField,
    Case,
    When,
    Value, StdDev
)
from django.db.models.functions import TruncDate, FirstValue, Lag, Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Quote


def calculate_fibonacci_levels(current_price, high, low):
    """
    Calculate Fibonacci retracement and extension levels.
    """
    # Ensure all inputs are Decimals
    current_price = Decimal(current_price)
    high = Decimal(high)
    low = Decimal(low)

    diff = high - low
    levels = {
        "23.6%": high - (diff * Decimal("0.236")),
        "38.2%": high - (diff * Decimal("0.382")),
        "50.0%": high - (diff * Decimal("0.5")),
        "61.8%": high - (diff * Decimal("0.618")),
        "78.6%": high - (diff * Decimal("0.786")),
        "current_price": current_price,
    }
    return {k: round(v, 4) for k, v in levels.items()}


# def get_daily_quotes_queryset(ticker, days=28, use_bucket=False):
#     """
#     Fetches the latest daily quotes for the given ticker.
#     """
#     now = timezone.now()
#     start_date = now - timedelta(days=days)
#     latest_daily_timestamps = (
#         Quote.objects.filter(company__ticker=ticker, time__range=(start_date, now))
#         .annotate(date=TruncDate('time'))
#         .values('company', 'date')
#         .annotate(latest_time=Max('time'))
#         .values('latest_time')
#     )
#     timestamps = [x['latest_time'] for x in latest_daily_timestamps]
#     qs = Quote.objects.filter(
#         company__ticker=ticker,
#         time__range=(start_date, now),
#         time__in=timestamps
#     )
#     if use_bucket:
#         return qs.time_bucket('time', '1 day')
#     return qs


def calculate_bollinger_bands(ticker, days=20, queryset=None):
    """
    Calculate Bollinger Bands.
    """
    queryset = get_daily_quotes_queryset(ticker, days=days)
    data = queryset.aggregate(
        sma=Avg('close_price'),
        std_dev=StdDev('close_price')
    )
    if not data or data['sma'] is None or data['std_dev'] is None:
        return None
    sma = data['sma']
    std_dev = data['std_dev']
    upper_band = sma + (std_dev * 2)
    lower_band = sma - (std_dev * 2)
    return {
        "upper_band": round(upper_band, 4),
        "lower_band": round(lower_band, 4),
        "sma": round(sma, 4)
    }


def calculate_macd(ticker, queryset=None, short_period=12, long_period=26, signal_period=9):
    """
    Calculate MACD and Signal Line.
    """
    if queryset is None:
        queryset = get_daily_quotes_queryset(ticker, days=long_period + signal_period)

    # Extract close prices
    prices = queryset.values_list('close_price', flat=True)
    if len(prices) < long_period:
        return None

    # Calculate EMAs
    short_ema = calculate_ema(prices, short_period)
    long_ema = calculate_ema(prices, long_period)
    macd_line = [s - l for s, l in zip(short_ema, long_ema)]
    signal_line = calculate_ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]

    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(histogram[-1], 4)
    }


def calculate_ema(prices, period):
    """
    Helper function to calculate EMA.
    """
    multiplier = Decimal(2) / Decimal(period + 1)  # Convert multiplier to Decimal
    ema = [sum(prices[:period]) / period]  # Initial SMA (assumes prices are Decimals)
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def get_daily_quotes_queryset(ticker, days=28, use_bucket=False):
    now = timezone.now()
    start_date = now - timedelta(days=days)
    end_date = now
    latest_daily_timestamps = (
        Quote.objects.filter(company__ticker=ticker, time__range=(start_date - timedelta(days=40), end_date))
        .annotate(date=TruncDate('time'))
        .values('company', 'date')
        .annotate(latest_time=Max('time'))
        .values('company', 'date', 'latest_time')
        .order_by('date')
    )
    actual_timestamps = [x['latest_time'] for x in latest_daily_timestamps]
    qs = Quote.timescale.filter(
        company__ticker=ticker,
        time__range=(start_date, end_date),
        time__in=actual_timestamps
    )
    if use_bucket:
        return qs.time_bucket('time', '1 day')
    return qs


def get_daily_moving_averages(ticker, days=28, queryset=None):
    """
    Calculate daily moving averages (MA5 and MA20).

    Args:
        ticker (str): The ticker symbol.
        days (int): Number of days to include.
        queryset (callable): Function to fetch the queryset.

    Returns:
        dict: Moving averages (MA5 and MA20).
    """
    if queryset is None:
        queryset = get_daily_quotes_queryset(ticker=ticker, days=days)
    obj = queryset.annotate(
        ma_5=Window(
            expression=Avg('close_price'),
            order_by=F('time').asc(),
            partition_by=[],
            frame=RowRange(start=-4, end=0),
        ),
        ma_20=Window(
            expression=Avg('close_price'),
            order_by=F('time').asc(),
            partition_by=[],
            frame=RowRange(start=-19, end=0),
        )
    ).order_by('-time').first()
    if not obj:
        return None
    ma_5 = obj.ma_5
    ma_20 = obj.ma_20
    if ma_5 is None or ma_20 is None:
        return None
    if ma_5 <= 0 or ma_20 <= 0:
        return None
    return {
        "ma_5": float(round(ma_5, 4)),
        "ma_20": float(round(ma_20, 4))
    }


def get_price_target(ticker, days=28, queryset=None):
    """
    Calculate price targets based on historical data.

    Args:
        ticker (str): The ticker symbol.
        days (int): Number of days to include.
        queryset (callable): Function to fetch the queryset.

    Returns:
        dict: Current price, conservative target, aggressive target, and average price.
    """
    if queryset is None:
        queryset = get_daily_quotes_queryset(ticker, days=days)
    daily_data = (
        queryset
        .annotate(
            latest_price=Window(
                expression=FirstValue('close_price'),
                partition_by=[],
                order_by=F('time').desc()
            )
        )
        .aggregate(
            current_price=Max('latest_price'),
            avg_price=Avg('close_price'),
            highest=Max('high_price'),
            lowest=Min('low_price')
        )
    )

    if not daily_data:
        return None
    current_price = float(daily_data['current_price'])
    avg_price = float(daily_data['avg_price'])
    price_range = float(daily_data['highest']) - float(daily_data['lowest'])

    # Simple target based on average price and recent range
    conservative_target = current_price + (price_range * 0.382)  # 38.2% Fibonacci
    aggressive_target = current_price + (price_range * 0.618)  # 61.8% Fibonacci

    return {
        'current_price': round(current_price, 4),
        'conservative_target': round(conservative_target, 4),
        'aggressive_target': round(aggressive_target, 4),
        'average_price': round(avg_price, 4)
    }


def get_volume_trend(ticker, days=28, queryset=None):
    """
    Analyze recent volume trends.

    Args:
        ticker (str): The ticker symbol.
        days (int): Number of days to include.
        queryset (callable): Function to fetch the queryset.

    Returns:
        dict: Average volume, latest volume, and percentage change in volume.
    """
    if queryset is None:
        queryset = get_daily_quotes_queryset(ticker=ticker, days=days)
    start = -(days - 1)
    data = queryset.annotate(
        avg_volume=Window(
            expression=Avg('volume'),
            order_by=F('time').asc(),
            partition_by=[],
            frame=RowRange(start=start, end=0)
        )
    ).order_by('-time').first()

    if not data:
        return None
    vol = data.volume
    avg_vol = data.avg_volume
    volume_change = 0
    if vol is None or avg_vol is None:
        return None
    if vol > 0 and avg_vol > 0:
        volume_change = ((vol - avg_vol) / avg_vol) * 100
    return {
        'avg_volume': float(avg_vol),
        'latest_volume': int(vol),
        'volume_change_percent': float(volume_change)
    }


def calculate_rsi(ticker, days=28, queryset=None, period=14):
    """
    Calculate Relative Strength Index (RSI) using Django ORM.

    Args:
        ticker (str): Stock ticker symbol.
        days (int): Days in the price data (default: 28).
        queryset (callable): Function to fetch the queryset.
        period (int): RSI period (default: 14).

    Returns:
        dict: RSI value and component calculations.
    """
    # Get daily price data
    if period is None:
        period = int(days / 4)
    if queryset is None:
        queryset = get_daily_quotes_queryset(ticker, days=days, use_bucket=True)

    # Calculate price changes and gains/losses with explicit decimal conversion
    movement = queryset.annotate(
        closing_price=ExpressionWrapper(
            F('close_price'),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        ),
        prev_close=Window(
            expression=Lag('close_price'),
            order_by=F('bucket').asc(),
            partition_by=[],
            output_field=DecimalField(max_digits=10, decimal_places=4)
        )
    ).annotate(
        price_change=ExpressionWrapper(
            F('close_price') - F('prev_close'),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        ),
        gain=Case(
            When(price_change__gt=0,
                 then=ExpressionWrapper(
                     F('price_change'),
                     output_field=DecimalField(max_digits=10, decimal_places=4)
                 )),
            default=Value(0, output_field=DecimalField(max_digits=10, decimal_places=4)),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        ),
        loss=Case(
            When(price_change__lt=0,
                 then=ExpressionWrapper(
                     -F('price_change'),
                     output_field=DecimalField(max_digits=10, decimal_places=4)
                 )),
            default=Value(0, output_field=DecimalField(max_digits=10, decimal_places=4)),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        )
    )

    # Calculate initial averages for the first period
    initial_avg = movement.exclude(prev_close__isnull=True)[:period].aggregate(
        avg_gain=Coalesce(
            ExpressionWrapper(
                Avg('gain'),
                output_field=DecimalField(max_digits=10, decimal_places=4)
            ),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=4))
        ),
        avg_loss=Coalesce(
            ExpressionWrapper(
                Avg('loss'),
                output_field=DecimalField(max_digits=10, decimal_places=4)
            ),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=4))
        )
    )

    # Get subsequent data points for EMA calculation
    subsequent_data = list(movement.exclude(prev_close__isnull=True)[period:].values('gain', 'loss'))

    # Calculate EMA-based RSI
    avg_gain = initial_avg['avg_gain']
    avg_loss = initial_avg['avg_loss']
    alpha = Decimal(1 / period)  # Smoothing factor

    # Update moving averages using EMA formula
    for data in subsequent_data:
        avg_gain = (avg_gain * (1 - alpha) + data['gain'] * alpha)
        avg_loss = (avg_loss * (1 - alpha) + data['loss'] * alpha)

    # Prevent division by zero
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    return {
        'rsi': round(float(rsi), 4),
        'avg_gain': round(float(avg_gain), 4),
        'avg_loss': round(float(avg_loss), 4),
        'period': period,
        'days': days,
    }


def get_stock_indicators(ticker="C:USDJPY", days=30):
    # Step 1: Fetch raw data
    queryset = get_daily_quotes_queryset(ticker, days=days)
    if queryset.count() == 0:
        raise Exception(f"Data for {ticker} not found")

    # Step 2: Fetch or calculate indicators
    # Averages and trends
    averages = get_daily_moving_averages(ticker, days=days, queryset=queryset)
    price_target = get_price_target(ticker, days=days, queryset=queryset)
    volume_trend = get_volume_trend(ticker, days=days, queryset=queryset)

    # RSI
    rsi_data = calculate_rsi(ticker, days=days, period=14)

    # Bollinger Bands
    bollinger_bands = calculate_bollinger_bands(ticker, days=days, queryset=queryset)

    # MACD
    macd_data = calculate_macd(ticker, queryset=queryset)

    # Fibonacci levels
    recent_high = queryset.aggregate(Max('high_price'))['high_price__max']
    recent_low = queryset.aggregate(Min('low_price'))['low_price__min']
    current_price = queryset.latest('time').close_price

    fibonacci_levels = (
        calculate_fibonacci_levels(current_price, recent_high, recent_low)
        if recent_high and recent_low
        else None
    )

    # Step 3: Generate trading signals
    signals = []
    # Moving averages: Compare short-term vs long-term MA
    if averages.get('ma_5') and averages.get('ma_20') and averages['ma_5'] > averages['ma_20']:
        signals.append(1)  # Bullish
    else:
        signals.append(-1)  # Bearish

    # Price target: Compare current price with conservative target
    if price_target.get('current_price') and price_target.get('conservative_target') and \
            price_target['current_price'] < price_target['conservative_target']:
        signals.append(1)  # Bullish
    else:
        signals.append(-1)  # Bearish

    # Volume trend: Check for significant volume change
    volume_change_percent = volume_trend.get("volume_change_percent")
    if volume_change_percent is not None:
        if volume_change_percent > 20:
            signals.append(1)  # Bullish
        elif volume_change_percent < -20:
            signals.append(-1)  # Bearish
        else:
            signals.append(0)  # Neutral

    # RSI: Overbought or oversold condition
    rsi = rsi_data.get('rsi')
    if rsi:
        if rsi > 70:
            signals.append(-1)  # Overbought (sell)
        elif rsi < 30:
            signals.append(1)  # Oversold (buy)
        else:
            signals.append(0)  # Neutral

    # Bollinger Bands: Check if price is above/below the bands
    if bollinger_bands:
        if current_price > bollinger_bands["upper_band"]:
            signals.append(-1)  # Overbought (sell)
        elif current_price < bollinger_bands["lower_band"]:
            signals.append(1)  # Oversold (buy)
        else:
            signals.append(0)  # Neutral

    # MACD: Bullish or bearish trend
    if macd_data:
        macd_histogram = macd_data.get("histogram")
        if macd_histogram:
            if macd_histogram > 0:
                signals.append(1)  # Bullish (buy)
            else:
                signals.append(-1)  # Bearish (sell)

    # Step 4: Combine and return results
    return {
        "score": sum(signals),
        "ticker": ticker,
        "indicators": {
            **averages,
            **price_target,
            **volume_trend,
            **rsi_data,
            **(bollinger_bands or {}),
            **(macd_data or {}),
            **(fibonacci_levels or {}),
        },
    }


def detect_market_trend(data):
    """
    Detect whether the market is bullish or bearish based on indicators.
    :param data: A dictionary containing stock indicators.
    :return: A string indicating 'bullish', 'bearish', or 'neutral'.
    """
    ma_5 = data.get("ma_5")
    ma_20 = data.get("ma_20")
    rsi = data.get("rsi")
    volume_change = data.get("volume_change_percent")
    current_price = data.get("current_price")
    upper_band = data.get("upper_band")
    lower_band = data.get("lower_band")

    # Check Moving Averages
    if ma_5 > ma_20:
        trend = "bullish"
    elif ma_5 < ma_20:
        trend = "bearish"
    else:
        trend = "neutral"

    # Incorporate RSI
    if rsi > 70:
        trend = "bearish"  # Overbought
    elif rsi < 30:
        trend = "bullish"  # Oversold

    # Use Bollinger Bands for further confirmation
    if current_price > upper_band:
        trend = "bearish"  # Price above the band suggests overbought.
    elif current_price < lower_band:
        trend = "bullish"  # Price below the band suggests oversold.

    # Volume Trend
    if volume_change > 20 and trend == "bullish":
        return "bullish"
    elif volume_change < -20 and trend == "bearish":
        return "bearish"

    return trend
