import logging
import pandas as pd
import os
import investment.constants as constants
from django.core.management.base import BaseCommand
from datetime import datetime, timezone
from utils.utils import delete_all_except_latest_file
from investment.models import TradingView

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "A command to upload Tradingview worksheet."

    def handle(self, *args, **options) -> str | None:

        """All functions need wrapping in the handle function"""
        def get_last_file():
            most_recent_file = None
            most_recent_time = 0
            # iterate over the files in the directory using os.scandir
            for entry in os.scandir(constants.TV_DATA_DIRECTORY_PATH):
                if entry.is_file():
                    # get the modification time of the file using entry.stat().st_mtime_ns
                    mod_time = entry.stat().st_mtime_ns
                    if mod_time > most_recent_time:
                        most_recent_file = entry.name
                        most_recent_time = mod_time
            most_recent_time_seconds = most_recent_time // 1000000000  # Convert nanoseconds to seconds
            # Create a timezone-aware UTC datetime object
            dt = datetime.fromtimestamp(most_recent_time_seconds, tz=timezone.utc)

            print("Latest file time: ", dt.strftime('%Y-%m-%d %H:%M:%S'))
            print("Deleting old files if necessary.")
            # This utility function will delete every old file in the specified directory
            update_bool = delete_all_except_latest_file(most_recent_file, constants.TV_DATA_DIRECTORY_PATH)
            return most_recent_file, update_bool

        def update_tbl_trading_view():
            msg = f"No new TradingView csv found in {constants.TV_DATA_DIRECTORY_PATH} folder."
            # Trading view update, update_time was used
            file, update_bool = get_last_file()
            # If a new file is found then truncate etc, else ignore
            if update_bool:
                path = os.path.join(constants.TV_DATA_DIRECTORY_PATH, file)
                df_tv = pd.read_csv(path)
                cols = list(constants.TRADINGVIEW_COLS.keys())
                df_tv = df_tv[cols]
                df_tv = df_tv.rename(columns=constants.TRADINGVIEW_COLS)
                if df_tv.shape[0] > 0:
                    # Send for formatting
                    format_df(df=df_tv)
                else:
                    print("Dataframe empty. Check.")


        def format_df(df):
            """Do all necessary formatting before sending to db"""
            # Drop duplicate tickers
            df = df.drop_duplicates(subset=['ticker'])
            # Get columns that are not of object type
            col_types = constants.TRADINGVIEW_DTYPES
            for col in df.columns:
                if col in col_types.keys():
                    if col_types[col]["dtype"] == "float64":
                        df[col] = pd.to_numeric(df[col], errors="coerce")
            # Send formatted df to the db
            send_df_to_db(df=df)

        def send_df_to_db(df):
            """Try to send df to database"""
            # Send to db after fetching table name
            table_name = constants.TRADINGVIEW_TABLE
            try:
                model_instances = [TradingView(**row) for index, row in df.iterrows()]
                TradingView.objects.bulk_create(model_instances)
            except Exception as e:
                log_str = f"Could not send df to table {table_name} in the db. Error Code: {e}"
                logger.error(log_str)

        update_tbl_trading_view()
