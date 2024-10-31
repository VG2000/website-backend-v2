from rest_framework import viewsets, generics
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models.functions import Coalesce, Round
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import (
    Subquery,
    OuterRef,
    CharField,
    FloatField,
    IntegerField,
    F,
    Q,
    ExpressionWrapper,
    Value
)
from .models import (
    ManualMeta,
    MonthlyVolume,
    WeeklyVolume,
    TradingView,
    Equity,
    Etp,
    Bond,
    Watchlist,
    CurrentInvestment,
    Book,
    Currency,
)
from .serializers import (
    TradingviewObjectiveSerializer,
    WatchlistSerializer,
    CurrentInvestmentSerializer,
    BookSerializer,
)
from datetime import timedelta, date, datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import *
import investment.constants as constants
import pandas as pd
import csv
import io
import environ
import logging
import requests
import warnings
import boto3
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from django.http import HttpResponse, HttpResponseNotFound
from investment.utils.response_utils import json_response
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Get an instance of environ and fetch AWS credentials
env = environ.Env()
environ.Env.read_env()
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = env("AWS_DEFAULT_REGION")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")


def test_s3_connection(bucket_name):
    logger.info("Entered test_s3_connection.. Creating boto3.client object...")
    s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION,
    config=Config(
            connect_timeout=10,  # Time in seconds before a connection attempt times out
            read_timeout=15,  # Time in seconds for read timeout
            retries={
                'max_attempts': 3,  # Number of retry attempts for the connection
                'mode': 'standard'
            }
        )
)
    try:
        logger.info("s3 client created.. Testing connection...")
        response = s3.head_bucket(Bucket=bucket_name)
        logger.info(f"S3 connection successful: {response}")
    except Exception as e:
        logger.error(f"Failed to connect to bucket {bucket_name} on S3: {e}")


# @permission_classes([IsAuthenticated])
def download_csv_from_s3(bucket_name, s3_file_path, local_file_path, download_file_name):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
    )
    try:
        logger.info("Starting download from S3...")
        with open(local_file_path, 'wb') as f:
            s3.download_fileobj(bucket_name, s3_file_path, f)
        logger.info("Download completed.")

        # Verify the file content after downloading
        with open(local_file_path, "rb") as f:
            csv_content = f.read()
            if csv_content:
                logger.info(f"File read successfully. Size: {len(csv_content)} bytes.")
                return csv_content
            else:
                logger.error("File is empty.")
                response = HttpResponse(csv_content, content_type="text/csv")
                response["Content-Disposition"] = (
                    f'attachment; filename="{download_file_name}"'
                )
                return response

    except (NoCredentialsError, PartialCredentialsError):
        logger.error("Credentials not available.")
        return HttpResponse("Credentials not available", status=403)
    except s3.exceptions.NoSuchKey:
        logger.error("The requested file does not exist on S3.")
        return HttpResponseNotFound("The requested file does not exist on S3")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return HttpResponse(f"An error occurred: {str(e)}", status=500)


def upload_tradingview_csv_to_db(file):
            logger.debug("Reading CSV file into DataFrame")
            try:
                df_tv = pd.read_csv(io.BytesIO(file))
                logger.info(f"CSV loaded successfully with {df_tv.shape[0]} rows and columns: {list(df_tv.columns)}")
            except Exception as e:
                logger.error(f"Failed to load CSV: {e}")
                log_str = f"Failed to load CSV: {e}"
                status_txt = "error"
                status = 500
                return json_response(log_str, status_txt, status)

            cols = list(constants.TRADINGVIEW_COLS.keys())

            try:
                df_tv = df_tv[cols]
                logger.info("CSV columns matched successfully.")
            except Exception as e:
                logger.error(f"CSV columns do not match expected values: {e}")
                log_str = f"CSV columns do not match expected values: {e}"
                status_txt = "error"
                status = 400
                return json_response(log_str, status_txt, status)

            df_tv = df_tv.rename(columns=constants.TRADINGVIEW_COLS)
            if df_tv.shape[0] > 0:
                logger.info("Processing DataFrame and preparing for database update.")

                # Send for formatting
                df = format_df(df=df_tv)

                # Convert DataFrame to a list of dictionaries
                dicts = df.to_dict("records")

                # Fetch existing tickers to determine which rows need updates vs. creates
                existing_tickers = set(
                    TradingView.objects.filter(
                        ticker__in=[row["ticker"] for row in dicts]
                    ).values_list("ticker", flat=True)
                )

                new_objs = []
                update_objs = []

                for row in dicts:
                    if row["ticker"] in existing_tickers:
                        update_objs.append(TradingView(**row))
                    else:
                        new_objs.append(TradingView(**row))

                logger.debug(f"Prepared {len(new_objs)} new objects and {len(update_objs)} updates for the database.")

                # Using Django's atomic transaction to ensure data integrity
                with transaction.atomic():
                    # Bulk create new objects
                    TradingView.objects.bulk_create(
                        new_objs, ignore_conflicts=True
                    )
                    logger.info(f"Bulk created {len(new_objs)} new records.")

                    # Bulk update existing objects
                    if update_objs:
                        for obj in update_objs:
                            TradingView.objects.filter(ticker=obj.ticker).update(
                                **{field: getattr(obj, field) for field in df.columns}
                            )
                        logger.info(f"Bulk updated {len(update_objs)} existing records.")

                log_str = "TradingView Updated"
                status_txt = "success"
                status = 200
                return json_response(log_str, status_txt, status)

            else:
                logger.warning("No new rows found in the TradingView CSV.")
                log_str = "New TradingView csv not found."
                status_txt = "success"
                status = 204
                return json_response(log_str, status_txt, status)


# @permission_classes([IsAuthenticated])
def upload_to_s3(file_obj, bucket_name, object_name):
    """
    Upload a file to an S3 bucket
    :param file_obj: File object to upload
    :param bucket_name: Bucket to upload to
    :param object_name: S3 object name
    :return: True if file was uploaded, else False
    """
    print("upload_to_s3 running....", upload_to_s3)
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
    )
    try:
        s3_client.upload_fileobj(file_obj, bucket_name, object_name)
        print(f"File uploaded to bucket '{bucket_name}' as '{object_name}'")
        upload_tradingview_csv_to_db(file_obj)
        return True
    except NoCredentialsError:
        print("Credentials not available")
        return False

class TradingViewCSVUploadAPIView(APIView):
    # permission_classes = [IsAuthenticated]  # Uncomment if you want to enforce authentication

    def post(self, request):
        # Check if a file is provided in the request
        file = request.FILES.get('file')
        if not file:
            logger.error("No file provided in the request.")
            return Response({"message": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        logger.debug("Reading CSV file into DataFrame")
        try:
            df_tv = pd.read_csv(io.BytesIO(file.read()))
            logger.info(f"CSV loaded successfully with {df_tv.shape[0]} rows and columns: {list(df_tv.columns)}")
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return Response({"message": f"Failed to load CSV: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        cols = list(constants.TRADINGVIEW_COLS.keys())

        try:
            df_tv = df_tv[cols]
            logger.info("CSV columns matched successfully.")
        except Exception as e:
            logger.error(f"CSV columns do not match expected values: {e}")
            return Response({"message": f"CSV columns do not match expected values: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        df_tv = df_tv.rename(columns=constants.TRADINGVIEW_COLS)
        if df_tv.shape[0] > 0:
            logger.info("Processing DataFrame and preparing for database update.")

            # Send for formatting
            df = format_df(df=df_tv)

            # Convert DataFrame to a list of dictionaries
            dicts = df.to_dict("records")

            # Fetch existing tickers to determine which rows need updates vs. creates
            existing_tickers = set(
                TradingView.objects.filter(
                    ticker__in=[row["ticker"] for row in dicts]
                ).values_list("ticker", flat=True)
            )

            new_objs = []
            update_objs = []

            for row in dicts:
                if row["ticker"] in existing_tickers:
                    update_objs.append(TradingView(**row))
                else:
                    new_objs.append(TradingView(**row))

            logger.debug(f"Prepared {len(new_objs)} new objects and {len(update_objs)} updates for the database.")

            # Using Django's atomic transaction to ensure data integrity
            with transaction.atomic():
                # Bulk create new objects
                TradingView.objects.bulk_create(
                    new_objs, ignore_conflicts=True
                )
                logger.info(f"Bulk created {len(new_objs)} new records.")

                # Bulk update existing objects
                if update_objs:
                    for obj in update_objs:
                        TradingView.objects.filter(ticker=obj.ticker).update(
                            **{field: getattr(obj, field) for field in df.columns}
                        )
                    logger.info(f"Bulk updated {len(update_objs)} existing records.")

            return Response({"message": "TradingView Updated"}, status=status.HTTP_200_OK)

        else:
            logger.warning("No new rows found in the TradingView CSV.")
            return Response({"message": "New TradingView csv not found."}, status=status.HTTP_204_NO_CONTENT)


class TradingviewObjectiveViewSet(viewsets.ModelViewSet):
    # permission_classes = [IsAuthenticated]
    serializer_class = TradingviewObjectiveSerializer

    def get_queryset(self):
        # Subquery to fetch fields from ManualMeta
        subquery_mm = ManualMeta.objects.filter(ticker=OuterRef("ticker")).values(
            "asset_class",
            "country__name",
            "sub_region__name",
            "region__name",
            "objective",
            "hedge_ccy",
        )[:1]

        # Subquery to fetch fields from Monthly Volume
        subquery_mv = (
            MonthlyVolume.objects.filter(ticker=OuterRef("ticker"))
            .values("gbp_turnover", "number_of_trades", "volume", "avg_trade_size")
            .annotate(
                turnover_monthly=F("gbp_turnover"),
                num_trades_monthly=F("number_of_trades"),
                volume_monthly=F("volume"),
                avg_trade_size_monthly=F("avg_trade_size"),
            )
            .values(
                "turnover_monthly",
                "num_trades_monthly",
                "volume_monthly",
                "avg_trade_size_monthly",
            )[:1]
        )

        # Subquery to fetch fields from Weekly Volume
        subquery_wv = (
            WeeklyVolume.objects.filter(ticker=OuterRef("ticker"))
            .values("gbp_turnover", "number_of_trades", "avg_spread", "avg_trade_size")
            .annotate(
                turnover_weekly=F("gbp_turnover"),
                num_trades_weekly=F("number_of_trades"),
                avg_trade_size_weekly=F("avg_trade_size"),
            )
            .values(
                "turnover_weekly",
                "num_trades_weekly",
                "avg_spread",
                "avg_trade_size_weekly",
            )[:1]
        )

        # Get trading_currency from Etp and Equity table
        equity_query = Equity.objects.filter(ticker=OuterRef("ticker")).values(
            "trading_currency"
        )[:1]
        etp_query = Etp.objects.filter(ticker=OuterRef("ticker")).values(
            "trading_currency"
        )[:1]

        # Combine the individual querysets using union
        combined_query = equity_query.union(etp_query)

        # Use the combined queryset in a subquery for annotation to TradingView
        subquery_trading_currency = combined_query.values("trading_currency")[:1]

        # Main query for TradingView with the subquery
        queryset = TradingView.objects.annotate(
            asset_class=Subquery(
                subquery_mm.values("asset_class"), output_field=CharField()
            ),
            country=Subquery(
                subquery_mm.values("country__name"), output_field=CharField()
            ),
            region=Subquery(
                subquery_mm.values("region__name"), output_field=CharField()
            ),
            sub_region=Subquery(
                subquery_mm.values("sub_region__name"), output_field=CharField()
            ),
            objective=Subquery(
                subquery_mm.values("objective"), output_field=CharField()
            ),
            hedge_ccy=Subquery(
                subquery_mm.values("hedge_ccy"), output_field=CharField()
            ),
            turnover_monthly=Subquery(
                subquery_mv.values("turnover_monthly"), output_field=FloatField()
            ),
            num_trades_monthly=Subquery(
                subquery_mv.values("num_trades_monthly"), output_field=IntegerField()
            ),
            volume_monthly=Subquery(
                subquery_mv.values("volume_monthly"), output_field=FloatField()
            ),
            avg_trade_size_monthly=Subquery(
                subquery_mv.values("avg_trade_size_monthly"), output_field=FloatField()
            ),
            turnover_weekly=Subquery(
                subquery_wv.values("turnover_weekly"), output_field=FloatField()
            ),
            num_trades_weekly=Subquery(
                subquery_wv.values("num_trades_weekly"), output_field=IntegerField()
            ),
            avg_spread=Subquery(
                subquery_wv.values("avg_spread"), output_field=FloatField()
            ),
            avg_trade_size_weekly=Subquery(
                subquery_wv.values("avg_trade_size_weekly"), output_field=FloatField()
            ),
            trading_currency=Subquery(
                subquery_trading_currency, output_field=CharField()
            ),
        ).order_by("asset_class", "region", "country", "objective")

        # Caching watchlist and portfolio checks
        tickers = queryset.values_list("ticker", flat=True)
        watchlist = set(
            Watchlist.objects.filter(id__in=tickers).values_list("id", flat=True)
        )
        portfolio = set(
            CurrentInvestment.objects.filter(ticker__in=tickers).values_list(
                "ticker", flat=True
            )
        )

        self.request.watchlist_cache = watchlist
        self.request.portfolio_cache = portfolio

        return queryset


def months_between_dates(date1, date2):
    """Calculate the month diff to attach to instrument url."""
    # Ensure date1 is earlier than date2
    if date1 > date2:
        date1, date2 = date2, date1

    # Calculate the difference in years and months
    years_diff = date2.year - date1.year
    months_diff = date2.month - date1.month

    # Convert years and months to total months
    total_months = years_diff * 12 + months_diff

    return total_months


def format_df(df):
    """Do all necessary formatting before sending to db"""
    # Drop duplicate tickers
    df = df.drop_duplicates(subset=["ticker"])
    # Get columns that are not of object type
    col_types = constants.INSTRUMENT_DTYPES
    for col in df.columns:
        if col in col_types.keys():
            if col_types[col]["dtype"] == "datetime64":
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                # Replace perpetual bonds (31/12/9999) with None
                df[col] = df[col].replace({pd.NaT: None})
            if col_types[col]["dtype"] == "float64":
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# Create your views here.
class InstrumentUploadView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        """Fetch the latest instrument sheet from the London Stock Exchange website."""
        print("Fetching instruments....")
        # This is the date of the first spreadsheet on the LSE server
        start_date = constants.INSTRUMENT_START_DATE
        current_date = datetime.today()

        # Get the month prefix for url and build full url
        url_tail = months_between_dates(start_date, current_date)
        base_url = constants.INSTRUMENT_BASE_URL
        url = f"{base_url}{url_tail}.xlsx"

        # Try and fetch the url
        res = requests.get(url)
        # If status 404 the get previous month
        if res.status_code == 404:
            url_tail = url_tail - 1
            url = f"{base_url}{url_tail}.xlsx"
        # Try and fetch the either this month or last month
        res = requests.get(url)
        print("Fetching: ", {url})
        print("res.staus.code: ", res.status_code)
        if res.status_code == requests.codes.ok:
            log_str = (
                f"Instrument URL successfully fetched. Status Code: {res.status_code}"
            )
            logger.info(log_str)
            # This will ensure that only the first iteration clears the table, every other df is appended
            etp_table_cleared = False
            # Try to read to dataframe and suppress the warning about no default style
            warnings.simplefilter("ignore", category=UserWarning)
            for i in constants.INSTRUMENT_SHEET_MAP:
                try:
                    df = pd.read_excel(
                        io.BytesIO(res.content),
                        engine="openpyxl",
                        skiprows=constants.INSTRUMENT_SKIP_ROWS,
                        sheet_name=i,
                    )
                    # Restore warnings to their default behavior
                    warnings.resetwarnings()
                    # Map column names to lower case as there is no standard in workbook e.g. Start Date, Start date
                    df.columns = map(str.lower, df.columns)
                    # Rename columns with correct column names for insertion to db
                    df = df.rename(columns=constants.INSTRUMENT_SHEET_MAP[i])
                    # Fetch the columns we need from the mapping and filter the df to include only the columns needed in db
                    columns = constants.INSTRUMENT_SHEET_MAP[i].values()
                    df = df[columns]
                    # Check that df is not empty and get table name before sending for formatting
                    if len(df) > 0:
                        model = constants.INSTRUMENT_MODEL_MAP[i]["model"]
                        # Drop duplicates - LSE error
                        len_all_etfs = len(df)
                        df = df.drop_duplicates(subset=["ticker"])
                        num_duplicates = len_all_etfs - len(df)
                        df = format_df(df=df)
                        row_iter = df.iterrows()
                        # Can't figure out how to make this dynamic yet
                        if model == "Equity":
                            objs = [
                                Equity(
                                    ticker=row["ticker"],
                                    issuer_name=row["issuer_name"],
                                    instrument_name=row["instrument_name"],
                                    isin=row["isin"],
                                    mifir_identifier_code=row["mifir_identifier_code"],
                                    icb_industry=row["icb_industry"],
                                    icb_super_sector=row["icb_super_sector"],
                                    country_of_incorporation=row[
                                        "country_of_incorporation"
                                    ],
                                    start_date=row["start_date"],
                                    trading_currency=row["trading_currency"],
                                    mkt_cap_mm=row["mkt_cap_mm"],
                                    lse_market=row["lse_market"],
                                    fca_listing_category=row["fca_listing_category"],
                                    market_segment_code=row["market_segment_code"],
                                    market_sector_code=row["market_sector_code"],
                                )
                                for index, row in row_iter
                            ]

                        if model == "Bond":
                            objs = [
                                Bond(
                                    ticker=row["ticker"],
                                    issuer_name=row["issuer_name"],
                                    instrument_name=row["instrument_name"],
                                    isin=row["isin"],
                                    mifir_identifier_code=row["mifir_identifier_code"],
                                    mifir_sub_class_code=row["mifir_sub_class_code"],
                                    mifir_sub_class_name=row["mifir_sub_class_name"],
                                    start_date=row["start_date"],
                                    maturity_date=row["maturity_date"],
                                    coupon_interest_rate=row["coupon_interest_rate"],
                                    country_of_incorporation=row[
                                        "country_of_incorporation"
                                    ],
                                    trading_currency=row["trading_currency"],
                                    lse_market=row["lse_market"],
                                    fca_listing_category=row["fca_listing_category"],
                                    market_segment_code=row["market_segment_code"],
                                    market_sector_code=row["market_sector_code"],
                                )
                                for index, row in row_iter
                            ]

                        if model == "Etp":
                            objs = [
                                Etp(
                                    ticker=row["ticker"],
                                    issuer_name=row["issuer_name"],
                                    instrument_name=row["instrument_name"],
                                    isin=row["isin"],
                                    mifir_identifier_code=row["mifir_identifier_code"],
                                    start_date=row["start_date"],
                                    country_of_incorporation=row[
                                        "country_of_incorporation"
                                    ],
                                    trading_currency=row["trading_currency"],
                                    lse_market=row["lse_market"],
                                    fca_listing_category=row["fca_listing_category"],
                                    market_segment_code=row["market_segment_code"],
                                    market_sector_code=row["market_sector_code"],
                                )
                                for index, row in row_iter
                            ]
                        try:
                            match model:
                                case "Etp":
                                    # Check if etp table has been cleared
                                    if etp_table_cleared == False:
                                        Etp.objects.all().delete()
                                        etp_table_cleared = True
                                        Etp.objects.bulk_create(objs)
                                    else:
                                        Etp.objects.bulk_create(objs)
                                case "Equity":
                                    # Clear equity table before reinserting
                                    Equity.objects.all().delete()
                                    Equity.objects.bulk_create(objs)
                                case "Bond":
                                    # Clear bond table before reinserting
                                    Bond.objects.all().delete()
                                    Bond.objects.bulk_create(objs)
                            log_str = f"Instrument file uploaded. {num_duplicates} duplicates removed."
                            status_txt = "success"
                            status = 200
                        except Exception as e:
                            log_str = f"Error importing data. {e}"
                            status_txt = "error"
                            status = res.status_code
                    else:
                        log_str = f"Instrument dataframe is empty."
                        status_txt = "error"
                        status = res.status_code
                except Exception as e:
                    log_str = f"Error importing data. {e}"
                    status_txt = "error"
                    status = res.status_code
        else:
            print("Oh my god an error!: ")
            status_txt = "error"
            status = res.status_code
            log_str = f"Error fetching data. Server response code: {status}"
        return json_response(log_str, status_txt, status)

class MonthlyVolumesUploadView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the last month's date by taking the first day of this month and subtracting one day
        today = date.today()
        first_day_of_this_month = today.replace(day=1)
        last_month_date = first_day_of_this_month - timedelta(days=1)
        year = last_month_date.strftime("%Y")
        last_month_name = last_month_date.strftime("%B")
        last_month = ""
        # Construct the equity URL for the last month
        equity_url_tail = f"{last_month_name}%20{year}.xlsx"
        equity_url_base_url = constants.MONTHLY_EQUITY_BASE_URL
        equity_url = f"{equity_url_base_url}{equity_url_tail}"
        # Try and fetch the url
        try:
            # Attempt to fetch data for the last month
            res = requests.get(equity_url)
            if res.status_code != 200:
                # If not successful, attempt the month before last
                first_day_of_last_month = last_month_date.replace(day=1)
                previous_month_date = first_day_of_last_month - timedelta(days=1)
                prev_year = previous_month_date.strftime("%Y")
                prev_month_name = previous_month_date.strftime("%B")
                last_month = prev_month_name

                # Construct the URL for the month before last
                equity_url_tail = f"{prev_month_name}%20{prev_year}.xlsx"
                equity_url = f"{equity_url_base_url}{equity_url_tail}"

                # Attempt to fetch the data for the month before last
                res = requests.get(equity_url)

            # If still not successful, raise an exception to handle in except block
            if res.status_code != 200:
                raise Exception("Failed to fetch data for both months.")
            # If successful
            if res.status_code == requests.codes.ok:
                last_month = last_month_name
                log_str = f"Monthly volume URL successfully fetched. Status Code: {res.status_code}"
                logger.info(log_str)
                try:
                    df = pd.read_excel(
                        io.BytesIO(res.content),
                        engine="openpyxl",
                        skiprows=constants.MONTHLY_EQUITY_VOLUME_SKIP_ROWS,
                        sheet_name=constants.MONTHLY_EQUITY_SHEET,
                    )
                    # Map column names to lower case as there is no standard in workbook e.g. Start Date, Start date
                    df.columns = map(str.lower, df.columns)
                    # Rename columns with correct column names for insertion to db
                    df = df.rename(columns=constants.MONTHLY_EQUITY_VOLUME_MAP)
                    # Fetch the columns we need from the mapping and filter the df to include only the columns needed in db
                    columns = constants.MONTHLY_EQUITY_VOLUME_MAP.values()
                    df = df[columns]

                    # Calculate average size once column names have been normalised
                    df = df.assign(
                        avg_trade_size=lambda x: (x["gbp_turnover"] / x["number_of_trades"])
                    )
                    # Check that df is not empty and run for ETPs
                    if len(df) > 0:
                        df_equity = df
                        # Construct etp url
                        etp_url_tail = f"{last_month}%20{year}.xlsx"
                        etp_url_base_url = constants.MONTHLY_ETP_BASE_URL
                        etp_url = f"{etp_url_base_url}{etp_url_tail}"

                        # Try and fetch the url
                        res = requests.get(etp_url)
                        if res.status_code == requests.codes.ok:
                            log_str = f"Monthly volume URL successfully fetched. Status Code: {res.status_code}"
                            logger.info(log_str)
                            try:
                                df = pd.read_excel(
                                    io.BytesIO(res.content),
                                    engine="openpyxl",
                                    skiprows=constants.MONTHLY_ETP_VOLUME_SKIP_ROWS,
                                    sheet_name=constants.MONTHLY_ETP_SHEET,
                                )
                                # Map column names to lower case as there is no standard in workbook e.g. Start Date, Start date
                                df.columns = map(str.lower, df.columns)
                                # Rename columns with correct column names for insertion to db
                                df = df.rename(columns=constants.MONTHLY_ETP_VOLUME_MAP)
                                # Fetch the columns we need from the mapping and filter the df to include only the columns needed in db
                                columns = constants.MONTHLY_ETP_VOLUME_MAP.values()
                                df = df[columns]
                                # Calculate average size once column names have been normalised
                                df = df.assign(
                                    avg_trade_size=lambda x: (
                                        x["gbp_turnover"] / x["number_of_trades"]
                                    )
                                )
                                # Check that df is not empty and send df to ETP function
                                if len(df) > 0:
                                    df = pd.concat([df, df_equity])
                                    # Drop duplicates - LSE error
                                    len_all_etfs = len(df)
                                    df = df.drop_duplicates(subset=["ticker"])
                                    num_duplicates = len_all_etfs - len(df)
                                    df = format_df(df=df)
                                    row_iter = df.iterrows()
                                    # Can't figure out how to make this dynamic yet
                                    objs = [
                                        MonthlyVolume(
                                            ticker=row["ticker"],
                                            isin=row["isin"],
                                            gbp_turnover=row["gbp_turnover"],
                                            number_of_trades=row["number_of_trades"],
                                            avg_trade_size=row["avg_trade_size"],
                                            volume=row["volume"],
                                        )
                                        for index, row in row_iter
                                    ]
                                    try:
                                        MonthlyVolume.objects.all().delete()
                                        MonthlyVolume.objects.bulk_create(objs)
                                        log_str = f"File for {last_month} uploaded. {num_duplicates} duplicates removed."
                                        status_txt = "success"
                                        status = 200
                                        return json_response(log_str, status_txt, status)
                                    except Exception as e:
                                        log_str = f"Error importing data. {e}"
                                        status_txt = "error"
                                        status = res.status_code
                                        return json_response(log_str, status_txt, status)
                                else:
                                    log_str = f"Monthly dataframe is empty."
                                    status_txt = "error"
                                    status = res.status_code
                                    return json_response(log_str, status_txt, status)

                            except Exception as Argument:
                                log_str = f"Error while reading Equity Monthly Volume workbook. Error is: {Argument}"
                                status_txt = "error"
                                status = res.status_code
                                return json_response(log_str, status_txt, status)
                        else:
                            log_str = f"Equity Monthly Volume URL get request failed. Error Code: {res.status_code}"
                            status_txt = "error"
                            status = res.status_code
                        return json_response(log_str, status_txt, status)
                    else:
                        log_str = f"Equity Monthly Volume dataframe is empty."
                        status_txt = "error"
                        status = res.status_code
                        return json_response(log_str, status_txt, status)
                except Exception as Argument:
                    log_str = f"Error while reading Equity Monthly Volume workbook. Error is: {Argument}"
                    status_txt = "error"
                    status = res.status_code
                    return json_response(log_str, status_txt, status)
            else:
                log_str = f"Equity Monthly Volume URL get request failed. Error Code: {res.status_code}"
                status_txt = "error"
                status = res.status_code
                return json_response(log_str, status_txt, status)
        except Exception as e:
            # Handle exceptions and unsuccessful requests
            status = res.status_code if 'res' in locals() else 500  # Default to 500 if no response is available
            log_str = "Unable to fetch Monthly Volumes"
            status_txt = "error"
            status = res.status_code
            return json_response(log_str, status_txt, status)

class WeeklyVolumesUploadView(APIView):
    # permission_classes = [IsAuthenticated]

    def previous_friday(self, date, weeks_ago=0):
        logger.debug(f"Calculating previous Friday for date: {date} with weeks_ago: {weeks_ago}")
        last_friday = date - timedelta(days=(date.weekday() - 4) % 7)
        previous_friday = last_friday - timedelta(weeks=weeks_ago)
        logger.debug(f"Previous Friday calculated as: {previous_friday}")
        return previous_friday

    def construct_weekly_url_tail(self, date, weeks_ago=0):
        last_friday = self.previous_friday(date, weeks_ago)
        url_tail = f"{last_friday.day}%20{last_friday.strftime('%B')}%20{last_friday.year}.xlsx"
        logger.debug(f"Constructed URL tail: {url_tail} for date: {date} and weeks_ago: {weeks_ago}")
        return url_tail

    def fetch_weekly_volume(self, weeks_ago=0):
        url_tail = self.construct_weekly_url_tail(datetime.now(), weeks_ago)
        url = f"{constants.WEEKLY_BASE_URL}{url_tail}"
        response = requests.get(url)
        logger.info(f"Fetching URL: {url}")
        logger.debug(f"Response status for URL '{url}': {response.status_code}")
        return response, url_tail

    def get(self, request):
        logger.info("WeeklyVolumesUploadView GET request received.")
        
        # Initial fetch attempt
        response, url_tail = self.fetch_weekly_volume()
        
        # Retry logic if not found (404)
        if response.status_code == 404:
            logger.warning("Received 404. Trying to fetch previous week's data.")
            response, url_tail = self.fetch_weekly_volume(weeks_ago=1)

        if response.status_code == requests.codes.ok:
            logger.info(f"Successfully fetched data for URL tail: {url_tail}")
            try:
                # Load the Excel file content into a DataFrame
                df = pd.read_excel(
                    io.BytesIO(response.content),
                    engine="openpyxl",
                    skiprows=constants.WEEKLY_ETP_VOLUME_SKIP_ROWS,
                    sheet_name=constants.WEEKLY_ETP_VOLUME_SHEET,
                )
                logger.debug(f"DataFrame loaded with {len(df)} rows from {url_tail}")

                # Standardize columns and check for required columns
                df.columns = map(str.lower, df.columns)
                df = df.rename(columns=constants.WEEKLY_ETP_VOLUME_MAP)
                required_columns = constants.WEEKLY_ETP_VOLUME_MAP.values()
                df = df[required_columns]
                initial_count = len(df)
                logger.debug(f"DataFrame columns after renaming: {df.columns.tolist()}")

                # Drop duplicates and handle missing values in critical columns
                df = df.drop_duplicates(subset=["ticker"])
                logger.info(f"Dropped {initial_count - len(df)} duplicate rows. Rows remaining: {len(df)}")
                
                columns_to_check = ["avg_trade_size", "gbp_turnover", "number_of_trades", "avg_spread"]
                df[columns_to_check] = df[columns_to_check].replace("", pd.NA)
                df = df.dropna(subset=columns_to_check)
                logger.info(f"Dropped rows with empty critical fields. Rows remaining after cleanup: {len(df)}")

                if df.empty:
                    logger.warning("Equity Weekly Volume dataframe is empty after processing.")
                    return json_response("Equity Weekly Volume dataframe is empty.", "error", status.HTTP_204_NO_CONTENT)

                # Prepare data for database insertion
                objs = [
                    WeeklyVolume(
                        ticker=row["ticker"],
                        isin=row["isin"],
                        avg_trade_size=row["avg_trade_size"] or None,
                        gbp_turnover=row["gbp_turnover"] or None,
                        number_of_trades=row["number_of_trades"] or None,
                        avg_spread=row["avg_spread"] or None,
                    )
                    for _, row in df.iterrows()
                ]

                # Clear existing records and insert new data
                WeeklyVolume.objects.all().delete()
                WeeklyVolume.objects.bulk_create(objs)
                clean_url_tail = url_tail.replace("%20", " ").replace(".xlsx", "")
                logger.info(f"File for {clean_url_tail} uploaded successfully with {len(df)} records.")

                return Response({'message': f"File for {clean_url_tail} uploaded successfully."}, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Error processing Excel file: {str(e)}", exc_info=True)
                return json_response(f"Error reading workbook: {e}", "error", status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.error(f"Failed to fetch data. URL: {constants.WEEKLY_BASE_URL}{url_tail} - Status Code: {response.status_code}")
            return Response({'message': f"URL request failed. Error Code: {response.status_code}"}, status=response.status_code)


class TradingViewDownloadView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.debug("Entered TradingViewUploadView GET method")

        update_bool = True  # Time to move to S3
        if update_bool:
            logger.info("Downloading CSV from S3. Testing connection...")
            logger.info(f"AWS_STORAGE_BUCKET_NAME: {AWS_STORAGE_BUCKET_NAME}")
            test_s3_connection(AWS_STORAGE_BUCKET_NAME)
            file = download_csv_from_s3(
                bucket_name=AWS_STORAGE_BUCKET_NAME,
                s3_file_path="tradingview/tradingview.csv",
                local_file_path="/tmp/tradingview.csv",
                download_file_name="tradingview.csv",
            )
            if isinstance(file, HttpResponse):
                logger.error("Failed to download CSV from S3. Returning error response.")
                return file

            logger.debug("Reading CSV file into DataFrame")
            try:
                df_tv = pd.read_csv(io.BytesIO(file))
                logger.info(f"CSV loaded successfully with {df_tv.shape[0]} rows and columns: {list(df_tv.columns)}")
            except Exception as e:
                logger.error(f"Failed to load CSV: {e}")
                log_str = f"Failed to load CSV: {e}"
                status_txt = "error"
                status = 500
                return json_response(log_str, status_txt, status)

            cols = list(constants.TRADINGVIEW_COLS.keys())

            try:
                df_tv = df_tv[cols]
                logger.info("CSV columns matched successfully.")
            except Exception as e:
                logger.error(f"CSV columns do not match expected values: {e}")
                log_str = f"CSV columns do not match expected values: {e}"
                status_txt = "error"
                status = 400
                return json_response(log_str, status_txt, status)

            df_tv = df_tv.rename(columns=constants.TRADINGVIEW_COLS)
            if df_tv.shape[0] > 0:
                logger.info("Processing DataFrame and preparing for database update.")

                # Send for formatting
                df = format_df(df=df_tv)

                # Convert DataFrame to a list of dictionaries
                dicts = df.to_dict("records")

                # Fetch existing tickers to determine which rows need updates vs. creates
                existing_tickers = set(
                    TradingView.objects.filter(
                        ticker__in=[row["ticker"] for row in dicts]
                    ).values_list("ticker", flat=True)
                )

                new_objs = []
                update_objs = []

                for row in dicts:
                    if row["ticker"] in existing_tickers:
                        update_objs.append(TradingView(**row))
                    else:
                        new_objs.append(TradingView(**row))

                logger.debug(f"Prepared {len(new_objs)} new objects and {len(update_objs)} updates for the database.")

                # Using Django's atomic transaction to ensure data integrity
                with transaction.atomic():
                    # Bulk create new objects
                    TradingView.objects.bulk_create(
                        new_objs, ignore_conflicts=True
                    )
                    logger.info(f"Bulk created {len(new_objs)} new records.")

                    # Bulk update existing objects
                    if update_objs:
                        for obj in update_objs:
                            TradingView.objects.filter(ticker=obj.ticker).update(
                                **{field: getattr(obj, field) for field in df.columns}
                            )
                        logger.info(f"Bulk updated {len(update_objs)} existing records.")

                log_str = "TradingView Updated"
                status_txt = "success"
                status = 200
                return json_response(log_str, status_txt, status)

            else:
                logger.warning("No new rows found in the TradingView CSV.")
                log_str = "New TradingView csv not found."
                status_txt = "success"
                status = 204
                return json_response(log_str, status_txt, status)

        logger.warning("TradingView DataFrame empty. No updates performed.")
        log_str = "TradingView DataFrame empty. Check."
        status_txt = "success"
        status = 204
        return json_response(log_str, status_txt, status)

class UploadNoMetadataCSVView(APIView):

    def get(self, request):
        try:
            # Get a list of tickers from ManualMeta
            tickers_in_manualmeta = ManualMeta.objects.values_list("ticker", flat=True)

            # Query records in TradingView and MonthlyVolume that are not in ManualMeta
            result = TradingView.objects.filter(
                ~Q(ticker__in=tickers_in_manualmeta)
            ).filter(ticker__in=MonthlyVolume.objects.values_list("ticker", flat=True))

            # Use StringIO to create a file-like object
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["Ticker", "Description"])
            ticker_count = 0
            for record in result:
                writer.writerow([record.ticker, record.description])
                ticker_count += 1

            # Move to the beginning of the StringIO buffer
            csv_buffer.seek(0)

            # Define S3 bucket name and object name
            bucket_name = AWS_STORAGE_BUCKET_NAME
            folder_path = "tradingview"
            object_name = f"{folder_path}/not_in_manualmeta.csv"

            # Encode the StringIO buffer to bytes
            file_obj = io.BytesIO(csv_buffer.getvalue().encode("utf-8"))

            # Upload to S3
            if upload_to_s3(file_obj, bucket_name, object_name):
                log_str =  f"CSV file with {ticker_count} tickers has been uploaded to '{bucket_name}'"
                status_txt = "success"
                status=200
                return json_response(log_str, status_txt, status)
            else:
                log_str =  "CSV file could not be uploaded to S3"
                status_txt = "error"
                status=500
                return json_response(log_str, status_txt, status)
        except Exception as e:
            log_str = f"CSV file not downloaded. Error: {e}",
            status_txt = "error"
            status=500
            return json_response(log_str, status_txt, status)


class WatchlistCreateView(generics.CreateAPIView):
    # permission_classes = [IsAuthenticated]
    queryset = Watchlist.objects.all()
    serializer_class = WatchlistSerializer

    def perform_create(self, serializer):
        ticker_id = self.request.data.get("id")
        logger.debug(f"Received ticker_id: {ticker_id}")

        # Check if the ticker exists in the TradingView model
        if not TradingView.objects.filter(ticker=ticker_id).exists():
            logger.error(f"Ticker {ticker_id} does not exist in TradingView model")
            raise ValidationError(
                {"error": "Ticker does not exist in Tradingview model"}
            )

        # Create the watchlist entry
        logger.debug(f"Creating watchlist entry for ticker: {ticker_id}")
        serializer.save()
        logger.debug("Watchlist entry created successfully")


class WatchlistDeleteView(generics.DestroyAPIView):
    # permission_classes = [IsAuthenticated]
    queryset = Watchlist.objects.all()
    serializer_class = WatchlistSerializer
    lookup_field = "id"


class GetTemporaryCredentialsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sts_client = boto3.client("sts")
        try:
            response = sts_client.get_session_token(
                DurationSeconds=3600
            )  # 1 hour session
            credentials = response["Credentials"]
            return JsonResponse(
                {
                    "AccessKeyId": credentials["AccessKeyId"],
                    "SecretAccessKey": credentials["SecretAccessKey"],
                    "SessionToken": credentials["SessionToken"],
                    "Expiration": credentials["Expiration"],
                }
            )
        except NoCredentialsError:
            log_str = "Invalid AWS credentials"
            status_txt = "error"
            status=400
            return json_response(log_str, status_txt, status)


class GetPresignedUrlView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        s3_client = boto3.client("s3", region_name=AWS_DEFAULT_REGION)
        bucket_name = AWS_STORAGE_BUCKET_NAME
        file_type = request.GET.get("filetype")

        try:
            presigned_post = s3_client.generate_presigned_post(
                Bucket=bucket_name,
                Key="tradingview/tradingview.csv",
                Fields={"Content-Type": file_type},
                Conditions=[{"Content-Type": file_type}],
                ExpiresIn=3600,  # Expires in 1 hour
            )
            print("presigned_post: ", presigned_post)
            return JsonResponse(presigned_post)
        except NoCredentialsError:
            log_str = "Invalid AWS credentials"
            status_txt = "error"
            status=400
            return json_response(log_str, status_txt, status)


# View to fetch data
class CurrentInvestmentDetailView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Filter out investments with qty = 0 before performing annotations
            investments = CurrentInvestment.objects.filter(qty__gt=0)

            # Subqueries for fetching trading_currency from Etp and Equity models
            trading_currency_etp_subquery = Subquery(
                Etp.objects.filter(ticker=OuterRef("ticker")).values("trading_currency")[:1]
            )
            trading_currency_equity_subquery = Subquery(
                Equity.objects.filter(ticker=OuterRef("ticker")).values("trading_currency")[:1]
            )

            # Annotate investments with trading_currency (ETP first, then Equity)
            investments = investments.annotate(
                trading_currency=Coalesce(
                    trading_currency_etp_subquery,
                    trading_currency_equity_subquery,
                    output_field=CharField(),
                )
            )

            # Subquery to fetch the price from TradingView model
            price_subquery = Subquery(
                TradingView.objects.filter(ticker=OuterRef("ticker")).values('price')[:1]
            )

            # Annotate the price to the investments
            investments = investments.annotate(
                price=Round(price_subquery, 2)
            )

            # Annotate the calculated GBP value using the trading currency and current price
            investments = investments.annotate(
                calculated_gbp_value=Subquery(
                    Currency.objects.filter(name=OuterRef("trading_currency")).values("gbp_value")[:1]
                )
            )

            # Calculate the gbp_value field based on the quantity, price, and GBP value
            investments = investments.annotate(
                calculated_gbp_value=Round(
                    ExpressionWrapper(
                        F("qty") * F("price") * F("calculated_gbp_value"),
                        output_field=FloatField(),
                    )
                )
            )

            # Calculate the percentage change field (pct_chg)
            investments = investments.annotate(
                pct_chg=Round(
                    ExpressionWrapper(
                        (F("price") / F("avg_px") - Value(1)) * Value(100),
                        output_field=FloatField(),
                    ),
                    1
                )
            )

            # Subquery to fetch the technical rating from the TradingView model
            technical_rating_subquery = Subquery(
                TradingView.objects.filter(ticker=OuterRef("ticker")).values('technical_rating')[:1]
            )

            # Annotate the technical rating to the investments
            investments = investments.annotate(
                technical_rating=technical_rating_subquery
            )

            # Serialize the data
            serializer = CurrentInvestmentSerializer(investments, many=True)

            # Return the response
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print("An error occurred:", e)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateCurrentInvestmentView(APIView):
    # permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        data = request.data
        ticker = data.get("ticker")
        book = data.get("book")
        transaction_px = data.get("transaction_px")
        qty = data.get("qty")

        # Validate and convert qty and transaction_px
        try:
            qty = int(qty)
            transaction_px = float(transaction_px)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid data type for qty or transaction_px"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate and fetch the foreign key objects
        try:
            etp = Etp.objects.get(ticker=ticker)
            book_obj = Book.objects.get(name=book)
        except (Etp.DoesNotExist, Book.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the existing investment if it exists
        investment = CurrentInvestment.objects.filter(ticker=etp, book=book_obj).first()

        # Validate conditions for selling securities
        if qty < 0:  # Selling shares
            if not investment:  # No existing investment found
                return Response(
                    {"error": "Cannot sell a security you do not have a position in."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif investment.qty + qty < 0:  # Trying to sell more shares than owned
                return Response(
                    {
                        "error": "Cannot sell more shares than you currently own.",
                        "current_qty": investment.qty,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Handle existing or new investment creation
        try:
            if not investment:
                # Creating a new investment
                investment = CurrentInvestment.objects.create(
                    ticker=etp,
                    book=book_obj,
                    qty=qty if qty > 0 else 0,
                    avg_px=transaction_px,
                    current_px=transaction_px,
                )
            else:
                # Updating an existing investment
                total_qty = investment.qty + qty
                new_avg_px = (
                    (investment.qty * investment.avg_px) + (qty * transaction_px)
                ) / total_qty if total_qty != 0 else 0
                investment.qty = total_qty
                investment.avg_px = new_avg_px
                investment.current_px = transaction_px
                investment.save()

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Investment updated successfully",
            },
            status=status.HTTP_200_OK,
        )

class BookAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.debug("Entered BookAPIView GET method")

        try:
            # Retrieve all current books (investments)
            logger.info("Fetching all books from the database")
            books = Book.objects.all()

            # Serialize the data
            logger.debug(f"Serializing {books.count()} books")
            serializer = BookSerializer(books, many=True)

            # Log the successful operation
            logger.info("Successfully retrieved and serialized books")
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # Log the error if something goes wrong
            logger.error(f"Error occurred while fetching books: {e}")
            return Response({"error": "Failed to retrieve books"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetTemporaryCredentialsView(APIView):

    def get(self, request):
        sts_client = boto3.client("sts")
        try:
            response = sts_client.get_session_token(
                DurationSeconds=3600
            )  # 1 hour session
            credentials = response["Credentials"]
            return JsonResponse(
                {
                    "AccessKeyId": credentials["AccessKeyId"],
                    "SecretAccessKey": credentials["SecretAccessKey"],
                    "SessionToken": credentials["SessionToken"],
                    "Expiration": credentials["Expiration"],
                }
            )
        except NoCredentialsError:
            log_str = "Invalid AWS credentials"
            status_txt = "error"
            status=400
            return json_response(log_str, status_txt, status)


class GetPresignedUrlView(APIView):

    def get(self, request):
        s3_client = boto3.client("s3", region_name=AWS_DEFAULT_REGION)
        bucket_name = AWS_STORAGE_BUCKET_NAME
        file_type = request.GET.get("filetype")

        try:
            presigned_post = s3_client.generate_presigned_post(
                Bucket=bucket_name,
                Key="tradingview/tradingview.csv",
                Fields={"Content-Type": file_type},
                Conditions=[{"Content-Type": file_type}],
                ExpiresIn=3600,  # Expires in 1 hour
            )
            print("presigned_post: ", presigned_post)
            return JsonResponse(presigned_post)
        except NoCredentialsError:
            log_str = "Invalid AWS credentials"
            status_txt = "error"
            status=400
            return json_response(log_str, status_txt, status)

class UpdateCurrentInvestmentView(APIView):

    def put(self, request, *args, **kwargs):
        data = request.data
        ticker = data.get("ticker")
        book = data.get("book")
        transaction_px = data.get("transaction_px")
        qty = data.get("qty")

        # Validate and convert qty and transaction_px
        try:
            qty = int(qty)
            transaction_px = float(transaction_px)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid data type for qty or transaction_px"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate and fetch the foreign key objects
        try:
            etp = Etp.objects.get(ticker=ticker)
            book_obj = Book.objects.get(name=book)
        except (Etp.DoesNotExist, Book.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the existing investment if it exists
        investment = CurrentInvestment.objects.filter(ticker=etp, book=book_obj).first()

        # Validate conditions for selling securities
        if qty < 0:  # Selling shares
            if not investment:  # No existing investment found
                return Response(
                    {"error": "Cannot sell a security you do not have a position in."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif investment.qty + qty < 0:  # Trying to sell more shares than owned
                return Response(
                    {
                        "error": "Cannot sell more shares than you currently own.",
                        "current_qty": investment.qty,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Handle existing or new investment creation
        try:
            if not investment:
                # Creating a new investment
                investment = CurrentInvestment.objects.create(
                    ticker=etp,
                    book=book_obj,
                    qty=qty if qty > 0 else 0,
                    avg_px=transaction_px,
                    current_px=transaction_px,
                )
            else:
                # Updating an existing investment
                total_qty = investment.qty + qty
                new_avg_px = (
                    (investment.qty * investment.avg_px) + (qty * transaction_px)
                ) / total_qty if total_qty != 0 else 0
                investment.qty = total_qty
                investment.avg_px = new_avg_px
                investment.current_px = transaction_px
                investment.save()

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Investment updated successfully",
            },
            status=status.HTTP_200_OK,
        )

class BookAPIView(APIView):

    def get(self, request):
        # Retrieve all current investments
        books = Book.objects.all()
        # Serialize the data
        serializer = BookSerializer(books, many=True)
        # Return a response
        return Response(serializer.data, status=status.HTTP_200_OK)


class TestAPIView(APIView):
# permission_classes = [IsAuthenticated]
    def previous_friday(self, date, weeks_ago=0):
        # Calculate the previous Friday date
        last_friday = date - timedelta(days=(date.weekday() - 4) % 7)
        return last_friday - timedelta(weeks=weeks_ago)

    def construct_weekly_url_tail(self, date, weeks_ago=0):
        last_friday = self.previous_friday(date, weeks_ago)
        url_tail = f"{last_friday.day}%20{last_friday.strftime('%B')}%20{last_friday.year}.xlsx"
        logger.debug(f"Constructed URL tail: {url_tail}")
        return url_tail

    def fetch_weekly_volume(self, weeks_ago=0):
        url_tail = self.construct_weekly_url_tail(datetime.now(), weeks_ago)
        url = f"{constants.WEEKLY_BASE_URL}{url_tail}"
        try:
            logger.debug(f"Fetching URL: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Ensure the response status is 2xx
            logger.info(f"Fetching URL: {url} - Status: {response.status_code}")
            return response, url_tail
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from {url}: {e}")
            return None, url_tail  # Return url_tail even when there's an exception

    def get(self, request):
        response, url_tail = self.fetch_weekly_volume()
        if response is None:
            logger.error(f"Failed to fetch data for {url_tail}")
            return Response(
                {
                    'message': f"File for {url_tail} not found.",
                    'error': 'Failed to fetch data from external API.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {'message': f"File for {url_tail} uploaded successfully."},
            status=status.HTTP_200_OK
    )

class TestAPIView2(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.debug("Entered TradingViewUploadView GET method")
        logger.info("Downloading CSV from S3")
        # AWS S3 configuration
        bucket_name = 'website-public-bucket'
        s3_file_key = 'tradingview/tradingview.csv'
        local_file_path = '/tmp/tradingview.csv'  # Save to /tmp in the container

        # Create an S3 client using boto3
        s3_client = boto3.client('s3')

        try:
            # Open the file in binary write mode
            with open(local_file_path, 'wb') as f:
                # Stream the download in chunks
                s3_client.download_fileobj(bucket_name, s3_file_key, f)

            return JsonResponse({"message": "File downloaded successfully.", "file_path": local_file_path})

        except s3_client.exceptions.NoSuchKey:
            return JsonResponse({"error": "The specified key does not exist in the bucket."}, status=404)

        except (NoCredentialsError, PartialCredentialsError) as e:
            return JsonResponse({"error": f"Credentials issue: {str(e)}"}, status=403)

        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)