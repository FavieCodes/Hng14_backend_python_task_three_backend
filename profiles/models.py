import uuid
from django.db import models

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    gender = models.CharField(max_length=20, db_index=True)
    gender_probability = models.FloatField()
    age = models.IntegerField(db_index=True)
    age_group = models.CharField(max_length=20, db_index=True)
    country_id = models.CharField(max_length=2, db_index=True)
    country_name = models.CharField(max_length=100)
    country_probability = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gender']),
            models.Index(fields=['age_group']),
            models.Index(fields=['country_id']),
            models.Index(fields=['age']),
            models.Index(fields=['gender_probability']),
            models.Index(fields=['country_probability']),
        ]
    
    def to_dict(self, full=True):
        """Convert model instance to dictionary"""
        data = {
            'id': str(self.id),
            'name': self.name,
            'gender': self.gender,
            'age': self.age,
            'age_group': self.age_group,
            'country_id': self.country_id,
            'country_name': self.country_name,
        }
        
        if full:
            data.update({
                'gender_probability': self.gender_probability,
                'country_probability': self.country_probability,
                'created_at': self.created_at.isoformat().replace('+00:00', 'Z'),
            })
        
        return data
    
    def __str__(self):
        return f"{self.name} ({self.country_name})"