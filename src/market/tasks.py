from celery import shared_task
from datetime import timedelta

from django.apps import apps
from django.utils import timezone

import helpers.clients as helper_clients

from .utils import batch_insert_stock_data, batch_insert_forex_data, batch_insert_crypto_data


@shared_task
def sync_company_quotes(company_id=10, data_type="forex", days_ago=32, date_format="%Y-%m-%d", verbose=False):
    """
    Sync company quotes for a given data type (stock, forex, crypto).

    Args:
        company_id (int): The ID of the company.
        data_type (str): The type of data to sync (e.g., "stock", "forex", "crypto").
        days_ago (int): The number of days back to fetch data.
        date_format (str): Date format for the API call.
        verbose (bool): Whether to log details.
    """
    Company = apps.get_model("market", "Company")
    try:
        company_obj = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        raise Exception(f"Company ID {company_id} invalid")

    company_ticker = company_obj.ticker
    if not company_ticker:
        raise Exception(f"{company_ticker} invalid")

    now = timezone.now()
    start_date = now - timedelta(days=days_ago)
    to_date = (start_date + timedelta(days=days_ago + 1)).strftime(date_format)
    from_date = start_date.strftime(date_format)

    client = helper_clients.PolygonAPIClient(
        ticker=company_ticker,
        from_date=from_date,
        to_date=to_date
    )

    # Map data_type to batch_insert functions
    batch_insert_methods = {
        "stock": batch_insert_stock_data,
        "forex": batch_insert_forex_data,
        "crypto": batch_insert_crypto_data,
    }

    if data_type not in batch_insert_methods:
        raise ValueError(f"Invalid data_type '{data_type}'. Must be one of {list(batch_insert_methods.keys())}")

    # Fetch data and batch insert
    fetch_method = getattr(client, f"get_{data_type}_data", None)
    if not callable(fetch_method):
        raise ValueError(f"Client does not support fetching data for type '{data_type}'")

    dataset = fetch_method()
    if verbose:
        print(f"{data_type.capitalize()} dataset length:", len(dataset))

    batch_insert_methods[data_type](dataset=dataset, company_obj=company_obj, verbose=verbose)


@shared_task
def sync_all_data(days_ago=2):
    """
    Sync stock, forex, and crypto data for all active companies.

    Args:
        days_ago (int): The number of days back to fetch data.
    """
    Company = apps.get_model("market", "Company")
    companies = Company.objects.filter(active=True).values_list('id', flat=True)

    for company_id in companies:
        for data_type in ["stock", "forex", "crypto"]:
            sync_company_quotes.delay(company_id, data_type=data_type, days_ago=days_ago)


@shared_task
def sync_historical_data(data_type="forex", years_ago=5, company_ids=[], use_celery=True, verbose=False):
    """
    Sync historical data (stock, forex, crypto) for companies in chunks.

    Args:
        data_type (str): Type of data to sync (e.g., "stock", "forex", "crypto").
        years_ago (int): Number of years back to fetch data.
        company_ids (list): List of specific company IDs to sync.
        use_celery (bool): Whether to use Celery for task dispatch.
        verbose (bool): Whether to log progress.
    """
    Company = apps.get_model("market", "Company")
    qs = Company.objects.filter(active=True)
    if company_ids:
        qs = qs.filter(id__in=company_ids)
    companies = qs.values_list('id', flat=True)

    for company_id in companies:
        days_starting_ago = 30 * 12 * years_ago  # Approximate days for the given years
        batch_size = 30  # Fetch data in 30-day chunks

        for i in range(batch_size, days_starting_ago + 1, batch_size):
            if verbose:
                print(f"{data_type.capitalize()} Historical sync: {i} days ago")

            if use_celery:
                sync_company_quotes.delay(company_id, data_type=data_type, days_ago=i, verbose=verbose)
            else:
                sync_company_quotes(company_id, data_type=data_type, days_ago=i, verbose=verbose)

            if verbose:
                print(f"{i} days ago batch completed\n")
