from django.apps import apps


def batch_insert_stock_data(dataset, company_obj=None, batch_size=1000, verbose=False):
    StockQuote = apps.get_model('market', 'StockQuote')
    batch_size = 1000
    if company_obj is None:
        raise Exception(f"Batch failed. Company Object {company_obj} invalid")
    for i in range(0, len(dataset), batch_size):
        if verbose:
            print("Doing chunk", i)
        batch_chunk = dataset[i:i + batch_size]
        chunked_quotes = [
            StockQuote(company=company_obj, **data) for data in batch_chunk
        ]
        StockQuote.objects.bulk_create(chunked_quotes, ignore_conflicts=True)
        if verbose:
            print("finished chunk", i)
    return len(dataset)


def batch_insert_forex_data(dataset, company_obj=None, batch_size=1000, verbose=False):
    ForexQuote = apps.get_model('market', 'ForexQuote')
    batch_size = 1000
    if company_obj is None:
        raise Exception(f"Batch failed. Company Object {company_obj} invalid")
    for i in range(0, len(dataset), batch_size):
        if verbose:
            print("Doing chunk", i)
        batch_chunk = dataset[i:i + batch_size]
        chunked_quotes = [
            ForexQuote(company=company_obj, **data) for data in batch_chunk
        ]
        ForexQuote.objects.bulk_create(chunked_quotes, ignore_conflicts=True)
        if verbose:
            print("finished chunk", i)
    return len(dataset)


def batch_insert_crypto_data(dataset, company_obj=None, batch_size=1000, verbose=False):
    CryptoQuote = apps.get_model('market', 'CryptoQuote')
    batch_size = 1000
    if company_obj is None:
        raise Exception(f"Batch failed. Company Object {company_obj} invalid")
    for i in range(0, len(dataset), batch_size):
        if verbose:
            print("Doing chunk", i)
        batch_chunk = dataset[i:i + batch_size]
        chunked_quotes = [
            CryptoQuote(company=company_obj, **data) for data in batch_chunk
        ]
        CryptoQuote.objects.bulk_create(chunked_quotes, ignore_conflicts=True)
        if verbose:
            print("finished chunk", i)
    return len(dataset)
