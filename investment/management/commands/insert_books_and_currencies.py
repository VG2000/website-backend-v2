# myapp/management/commands/populate_models.py
from django.core.management.base import BaseCommand
from investment.models import Currency, Book

class Command(BaseCommand):
    help = 'Populate the Currency and Book models with initial data'

    def handle(self, *args, **kwargs):
        # Data to be inserted
        currencies = ['EUR', 'USD', 'GBX']
        books = ['ISA', 'SIPP', 'Trading']

        # Populate Currency model
        for code in currencies:
            gbp_value = 0.1 if code == 'GBX' else 1
            currency, created = Currency.objects.get_or_create(name=code, defaults={'gbp_value': gbp_value})
            if not created and code == 'GBX':
                # If the currency already exists and is GBX, update the gbp_value to 0.1
                currency.gbp_value = 0.1
                currency.save()
                self.stdout.write(self.style.WARNING(f'Currency {code} already exists, gbp_value updated to {gbp_value}'))

            elif created:
                self.stdout.write(self.style.SUCCESS(f'Successfully added currency: {code} with gbp_value {gbp_value}'))
            else:
                self.stdout.write(self.style.WARNING(f'Currency {code} already exists'))

        # Populate Book model
        for name in books:
            book, created = Book.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully added book: {name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Book {name} already exists'))

        self.stdout.write(self.style.SUCCESS('Finished populating Currency and Book models.'))
