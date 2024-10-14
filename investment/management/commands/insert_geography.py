from django.core.management.base import BaseCommand
import logging
import pandas as pd
import numpy as np
import os
from investment.models import Region, SubRegion, Country
from django.db import transaction
import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "A command to rebuild Region, SubRegion, Country tables to db. Run in that sequence"

    def handle(self, *args, **options):
        """All functions need wrapping in the handle function"""
        # Ensure csv file in the base path folder.
        base_path = os.getcwd() + "/investment/data/"

        self.upload_region(base_path)
        self.stdout.write(self.style.SUCCESS('Successfully inserted regions.'))
        self.upload_sub_region(base_path)
        self.stdout.write(self.style.SUCCESS('Successfully inserted sub regions.'))
        self.upload_country(base_path)
        self.stdout.write(self.style.SUCCESS('Successfully inserted countries.'))


    def upload_region(self, base_path):
        file = "region.csv"
        path = base_path + file
        model = Region
        print(os.getcwd())
        df = pd.read_csv(path)
        df = df.dropna()
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

    def upload_sub_region(self, base_path):
        file = "sub_region.csv"
        path = base_path + file
        model = SubRegion
        print(os.getcwd())
        df = pd.read_csv(path)
        df = df.dropna()
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
                region=region_instance,
                name=row['name'],
            )
            objs.append(model_instance)

        try:
            # Clear table before reinserting
            model.objects.all().delete()
            model.objects.bulk_create(objs)
        except Exception as e:
            print("Error: ", e)

    def upload_country(self, base_path):
        file = "country.csv"
        path = base_path + file
        model = Country
        print(os.getcwd())
        df = pd.read_csv(path)
        # df = df.fillna("NA")
        df = df.dropna()
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
                subregion=subregion_instance,
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
