from django.core.management.base import BaseCommand
import logging
import pandas as pd
import numpy as np
import os
from investment.models import ManualMeta, Region, SubRegion, Country
from django.db import transaction
logger = logging.getLogger(__name__)
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', )



class Command(BaseCommand):
    help = "A command to rebuild Region, SubRegion,Country and ManualMeta tables to db. Run in that sequence"
    def handle(self, *args, **options) -> str | None:
        """All functions need wrapping in the handle function"""
        # Ensure csv file in the base path folder.
        base_path = os.getcwd() + "/investment/management/commands/data/"

        def upload_objectives():
            file = "objectives.csv"
            path = base_path + file
            df = pd.read_csv(path)
            row_iter = df.iterrows()
            objs = []
            # Using Django's atomic transaction to ensure data integrity
            with transaction.atomic():
                for index, row in row_iter:
                    country_name = row['country']
                    region_name = row['region']
                    sub_region_name = row['sub_region']

                    # Use pd.isna to check for NaN values in pandas DataFrame
                    if pd.isna(region_name):
                        region_name = 'Global'

                    country_instance, _ = Country.objects.get_or_create(name=country_name)
                    region_instance, _ = Region.objects.get_or_create(name=region_name)
                    sub_region_instance, _ = SubRegion.objects.get_or_create(name=sub_region_name)

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
                    objs.append(model_instance)

                # Clear table before reinserting
                ManualMeta.objects.all().delete()
                ManualMeta.objects.bulk_create(objs)

        def upload_region():
             # ADD CSV NAME
            file = "region.csv"
            path = base_path + file
            # ADD MODEL NAME
            model = Region
            print(os.getcwd())
            df = pd.read_csv(path)
            # df.dropna(subset=['ticker'])
            df = df.fillna("NA")
            # print(df)
            row_iter = df.iterrows()
            objs = []
            for index, row in row_iter:
                model_instance = model(
                    name=row['name'],
                )
                objs.append(model_instance)

            try:
                # Clear table before reinserting
                model.objects.all().delete()
                model.objects.bulk_create(objs)
            except Exception as e:
                print("Error: ", e)

        def upload_sub_region():
             # ADD CSV NAME
            file = "sub_region.csv"
            path = base_path + file
            # ADD MODEL NAME
            model = SubRegion
            print(os.getcwd())
            df = pd.read_csv(path)
            # df.dropna(subset=['ticker'])
            df = df.fillna("NA")
            # print(df)
            row_iter = df.iterrows()
            objs = []
            for index, row in row_iter:
                region = row['region']
                try:
                    region_instance = Region.objects.get(name=region)
                except Region.DoesNotExist:
                    # Handle the case where the region does not exist
                    region_instance = None
                model_instance = model(
                    # MANUALLY ENSURE THAT THE FIELDS MATCH THE model
                    region = region_instance,
                    name=row['name'],
                )
                objs.append(model_instance)

            try:
                # Clear table before reinserting
                model.objects.all().delete()
                model.objects.bulk_create(objs)
            except Exception as e:
                print("Error: ", e)

        def upload_country():
             # ADD CSV NAME
            file = "country.csv"
            path = base_path + file
            # ADD MODEL NAME
            model = Country
            print(os.getcwd())
            df = pd.read_csv(path)
            # df.dropna(subset=['ticker'])
            df = df.fillna("NA")
            # print(df)
            row_iter = df.iterrows()
            objs = []
            for index, row in row_iter:
                subregion = row['sub_region']
                try:
                    subregion_instance = SubRegion.objects.get(name=subregion)
                except SubRegion.DoesNotExist:
                    # Handle the case where the subregion does not exist
                    subregion_instance = None
                model_instance = model(
                    # MANUALLY ENSURE THAT THE FIELDS MATCH THE model
                    subregion = subregion_instance,
                    name=row['name'],
                    alpha_2=row['alpha_2']

                )
                objs.append(model_instance)

            try:
                # Clear table before reinserting
                model.objects.all().delete()
                model.objects.bulk_create(objs)
            except Exception as e:
                print("Error: ", e)


        upload_objectives()
