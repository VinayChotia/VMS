from django.core.management.base import BaseCommand
from account.models import Site, Location, Section

class Command(BaseCommand):
    help = 'Populate master data for Site, Location, and Section'

    def handle(self, *args, **options):
        # 1. Define Sites
        sites_data = [
            {'name': 'Main Campus', 'code': 'S001', 'address': '123 Tech Park', 'daily_capacity_limit': 1000},
            {'name': 'Innovation Hub', 'code': 'S002', 'address': '456 Startup Way', 'daily_capacity_limit': 500},
        ]

        # 2. Define Locations and Sections for each site
        master_data = {
            'S001': {
                'locations': [
                    {
                        'name': 'Building A', 'code': 'L001', 'floor_number': 1,
                        'sections': [
                            {'name': 'Reception', 'code': 'SEC001', 'section_type': 'general', 'daily_capacity': 100, 'requires_escort': False},
                            {'name': 'Main Office', 'code': 'SEC002', 'section_type': 'general', 'daily_capacity': 200, 'requires_escort': False},
                            {'name': 'Server Room', 'code': 'SEC003', 'section_type': 'server', 'daily_capacity': 10, 'requires_escort': True},
                        ]
                    },
                    {
                        'name': 'Building B', 'code': 'L002', 'floor_number': 2,
                        'sections': [
                            {'name': 'R&D Lab', 'code': 'SEC004', 'section_type': 'lab', 'daily_capacity': 50, 'requires_escort': True},
                            {'name': 'Meeting Room 1', 'code': 'SEC005', 'section_type': 'conference', 'daily_capacity': 30, 'requires_escort': False},
                        ]
                    }
                ]
            },
            'S002': {
                'locations': [
                    {
                        'name': 'Innovation Center', 'code': 'L003', 'floor_number': 1,
                        'sections': [
                            {'name': 'Co-working Space', 'code': 'SEC006', 'section_type': 'general', 'daily_capacity': 150, 'requires_escort': False},
                            {'name': 'Executive Suite', 'code': 'SEC007', 'section_type': 'executive', 'daily_capacity': 20, 'requires_escort': True},
                        ]
                    }
                ]
            }
        }

        # 3. Create records
        for s_data in sites_data:
            site, created = Site.objects.get_or_create(
                code=s_data['code'],
                defaults={
                    'name': s_data['name'],
                    'address': s_data['address'],
                    'daily_capacity_limit': s_data['daily_capacity_limit']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Site: {site.name}'))
            else:
                self.stdout.write(f'Site already exists: {site.name}')

            site_content = master_data.get(site.code)
            if site_content:
                for l_data in site_content['locations']:
                    location, l_created = Location.objects.get_or_create(
                        site=site,
                        code=l_data['code'],
                        defaults={
                            'name': l_data['name'],
                            'floor_number': l_data.get('floor_number')
                        }
                    )
                    if l_created:
                        self.stdout.write(self.style.SUCCESS(f'  Created Location: {location.name}'))
                    else:
                        self.stdout.write(f'  Location already exists: {location.name}')

                    for sec_data in l_data['sections']:
                        section, s_created = Section.objects.get_or_create(
                            location=location,
                            code=sec_data['code'],
                            defaults={
                                'name': sec_data['name'],
                                'section_type': sec_data['section_type'],
                                'daily_capacity': sec_data['daily_capacity'],
                                'requires_escort': sec_data['requires_escort']
                            }
                        )
                        if s_created:
                            self.stdout.write(self.style.SUCCESS(f'    Created Section: {section.name}'))
                        else:
                            self.stdout.write(f'    Section already exists: {section.name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated master data.'))
