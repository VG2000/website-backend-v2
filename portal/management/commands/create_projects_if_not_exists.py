from django.core.management.base import BaseCommand
from portal.models import Project


class Command(BaseCommand):
    help = "Add a list of predefined projects to the Project model"

    def handle(self, *args, **kwargs):
        projects = [
            {
                "name": "ninety-nine",
                "is_public": False,
                "alt": "99%",
                "icon_url":"https://website-portfolio-bucket.s3.eu-west-2.amazonaws.com/project_icons/99pct.jpg",
                "description": "Built using React and Django, this is a project that aggregates news from a variety of international sources including the IMF and OECD as well aws domestic think tanks such as the Kings Fund and the Nuffield Trust ",
            },
            {
                "name": "my-mp",
                "is_public": True,
                "alt": "HoC",
                "icon_url":"https://website-portfolio-bucket.s3.eu-west-2.amazonaws.com/project_icons/Hoc.png",
                "description": "Using React, this is a project that fetches data using the UK Parliament API. It constructs a summary using the lates Register of Members Interests as well as providing static resources for a campaigner to build campaign material based on their findings.  ",
            },
            {
                "name": "ardent",
                "is_public": False,
                "alt": "Ardent",
                "icon_url":"https://website-portfolio-bucket.s3.eu-west-2.amazonaws.com/project_icons/ardentAvatar.png",
                "description": "Built using React, Django and PostgreSQL, this project was built for a small financial brokerage and was composed of a series of integrated components including a CRM interface, trading blotter, order management system as well as some tools to assist the research function such as programmatic EDGAR and SEC access. ",
            },
            {
                "name": "investment",
                "is_public": False,
                "alt": "ETF's",
                "icon_url":"https://website-portfolio-bucket.s3.eu-west-2.amazonaws.com/project_icons/investments.jpg",
                "description": "Built using React, Django and PostgreSQL, this is is the project that I use for managing my personal investments. It fetches every ETF and IT traded on the LSE along with weekly and monthly volumes and joins it to my algorithmic models from TradingView to give me a comprehensive view of c3000 possible investment opportunities globally.   ",
            },
        ]

        for project_data in projects:
            try:
                # Try to get the existing project by name
                project = Project.objects.get(name=project_data["name"])
                # Update the project with the new data
                project.is_public = project_data["is_public"]
                project.alt = project_data["alt"]
                project.icon_url = project_data["icon_url"]
                project.description = project_data["description"]
                project.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Project updated: {project.name}")
                )
            except Project.DoesNotExist:
                # If project does not exist, create a new one
                Project.objects.create(**project_data)
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully added project: {project_data['name']}")
                )

        # # Add portfolio_admiin
        # project, created = Project.objects.get_or_create(
        #         name='portfolio_admin',
        #         defaults={"is_public": False},
        #     )
        # if created:
        #     self.stdout.write(
        #         self.style.SUCCESS("Successfully added portfolio_admin")
        #     )
        # else:
        #     self.stdout.write(
        #         self.style.WARNING("portfolio_admin already exists")
        #     )


