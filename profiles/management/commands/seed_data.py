import json
import os
from django.core.management.base import BaseCommand
from profiles.models import Profile
from django.conf import settings

class Command(BaseCommand):
    help = 'Seed database with profile data from JSON file (idempotent)'
    
    def handle(self, *args, **options):
        # Try multiple possible file locations
        possible_paths = [
            os.path.join(settings.BASE_DIR, 'seed_profiles.json'),
            os.path.join(settings.BASE_DIR, 'profiles.json'),
            os.path.join(settings.BASE_DIR, 'data', 'seed_profiles.json'),
        ]
        
        json_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                json_file_path = path
                break
        
        if not json_file_path:
            self.stdout.write(self.style.ERROR(f"No seed file found. Tried: {possible_paths}"))
            return
        
        self.stdout.write(f"Loading profile data from: {json_file_path}")
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to read file: {e}"))
            return
        
        # Handle JSON structure
        if isinstance(data, dict) and 'profiles' in data:
            profiles_data = data['profiles']
            self.stdout.write(f"Found profiles array inside 'profiles' key")
        elif isinstance(data, list):
            profiles_data = data
            self.stdout.write(f"Found direct profiles array")
        else:
            self.stdout.write(self.style.ERROR(f"Unexpected JSON structure"))
            return
        
        self.stdout.write(f"Found {len(profiles_data)} profiles in file")
        
        profiles_created = 0
        profiles_skipped = 0
        
        for item in profiles_data:
            name = item.get('name', '').strip().lower()
            
            if not name:
                continue
            
            if Profile.objects.filter(name=name).exists():
                profiles_skipped += 1
                continue
            
            Profile.objects.create(
                name=name,
                gender=item.get('gender'),
                gender_probability=item.get('gender_probability'),
                age=item.get('age'),
                age_group=item.get('age_group'),
                country_id=item.get('country_id'),
                country_name=item.get('country_name'),
                country_probability=item.get('country_probability'),
            )
            profiles_created += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Seeding complete!\n"
            f"   Created: {profiles_created}\n"
            f"   Skipped (already exist): {profiles_skipped}\n"
            f"   Total in database: {Profile.objects.count()}"
        ))