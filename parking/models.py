from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Parking(models.Model):
    parking_id = models.IntegerField(primary_key=True)
    amount_of_spots = models.IntegerField()
    address = models.CharField(max_length=255)
    comment = models.CharField(max_length=255, blank=True, null=True)
    price = models.IntegerField()
    
    class Meta:
        db_table = 'parking'
        
    def __str__(self):
        return f"Parking {self.parking_id} - {self.address}"

class Booking(models.Model):
    booking_id = models.IntegerField(primary_key=True)
    parking_id = models.ForeignKey(Parking, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    class Meta:
        db_table = 'booking'
        
    def __str__(self):
        return f"Booking {self.booking_id} - {self.parking_id} - {self.user_id}"

