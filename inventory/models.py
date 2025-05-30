from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=50)  # เช่น 'admin', 'staff'

    def __str__(self):
        return f"{self.user.username} ({self.user_type})"


class MaterialStock(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    barcode = models.CharField(max_length=100)
    cost = models.FloatField()
    avg_cost = models.FloatField()
    unit = models.CharField(max_length=50)
    sale_price = models.FloatField()
    reorder_point = models.IntegerField()
    max_stock = models.IntegerField()
    category = models.CharField(max_length=50)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class MaterialOrder(models.Model):
    material = models.ForeignKey(MaterialStock, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0,null=True,blank=True)
    total_cost = models.FloatField(default=0,null=True,blank=True)
    ordered_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField(blank=True)



class MaterialOrderItem(models.Model):
    order = models.ForeignKey(MaterialOrder, related_name='items', on_delete=models.CASCADE)
    material = models.ForeignKey(MaterialStock, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.FloatField()
    total_cost = models.FloatField()


