from django.core.management.base import BaseCommand
import logging
import pandas as pd
import numpy as np
import os
from investment.models import ManualMeta, Region, SubRegion, Country
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "A command to rebuild Region, SubRegion, Country, and ManualMeta (upload_objectives) tables to db. Run in that sequence"

    def handle(self, *args, **options):
        """All functions need wrapping in the handle function"""
        # Ensure csv file in the base path folder.
        base_path = os.getcwd() + "/investment/data/"

        self.upload_objectives(base_path)
        self.stdout.write(self.style.SUCCESS('Successfully inserted objectives.'))

    def upload_objectives(self, base_path):
        file = "objectives.csv"
        path = base_path + file
        df = pd.read_csv(path)

        # Replace NaN values with appropriate placeholders or handle them as needed
        df.fillna({'country': 'N/A', 'region': 'Global', 'sub_region': 'N/A'}, inplace=True)

        row_iter = df.iterrows()
        objs = []

        # Using Django's atomic transaction to ensure data integrity
        with transaction.atomic():
            for index, row in row_iter:
                region_name = row['region']
                sub_region_name = row['sub_region']
                country_name = row['country']

                # Use pd.isna to check for NaN values in pandas DataFrame
                if pd.isna(region_name):
                    region_name = 'Global'

                # Fetch existing country instance if country_name is not None
                country_instance = None
                if country_name:
                    try:
                        country_instance = Country.objects.get(name=country_name)
                        # logger.info(f"Retrieved existing country: {country_instance.name}")
                    except Country.DoesNotExist:
                        # logger.warning(f"Country not found: {country_name}")
                        pass

                # Fetch existing region instance
                region_instance = None
                try:
                    region_instance = Region.objects.get(name=region_name)
                    # logger.info(f"Retrieved existing region: {region_instance.name}")
                except Region.DoesNotExist:
                    # logger.warning(f"Region not found: {region_name}")
                    pass

                # Fetch existing sub-region instance if sub_region_name is not None
                sub_region_instance = None
                if sub_region_name:
                    try:
                        sub_region_instance = SubRegion.objects.get(name=sub_region_name, region=region_instance)
                        # logger.info(f"Retrieved existing sub-region: {sub_region_instance.name}")
                    except SubRegion.DoesNotExist:
                        # logger.warning(f"Sub-region not found: {sub_region_name}")
                        pass

                # Check if the ticker already exists
                if not ManualMeta.objects.filter(ticker=row["ticker"]).exists():
                    model_instance = ManualMeta(
                        ticker=row["ticker"],
                        asset_class=row['asset_class'],
                        country=country_instance,
                        region=region_instance,
                        sub_region=sub_region_instance,
                        objective=row['objective'],
                        emerging_mkt=row['emerging_mkt'],
                        leverage_typ=row['leverage_typ'],
                        hedge_ccy=row['hedge_ccy'],
                        single_stock=row['single_stock']
                    )
                    # logger.info(f"Adding {model_instance.ticker} to bulk create list.")
                    objs.append(model_instance)
                else:
                    pass
                    # logger.info(f"Ticker {row['ticker']} already exists in ManualMeta.")

            # Bulk create only new records
            if objs:
                ManualMeta.objects.bulk_create(objs)
                logger.info(f"Bulk created {len(objs)} new ManualMeta records.")
            else:
                logger.info("No new ManualMeta records to create.")
