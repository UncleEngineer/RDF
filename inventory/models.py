# models.py - เพิ่ม DeliveryRound และ approval fields

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


class DeliveryRound(models.Model):
    """โมเดลสำหรับจัดการรอบจัดส่ง"""
    name = models.CharField(max_length=100, verbose_name="ชื่อรอบจัดส่ง")
    description = models.TextField(blank=True, verbose_name="รายละเอียด")
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "รอบจัดส่ง"
        verbose_name_plural = "รอบจัดส่ง"
        ordering = ['name']
    
    def __str__(self):
        return self.name


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
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'รออนุมัติ'),
        ('approved', 'อนุมัติแล้ว'),
        ('rejected', 'ไม่อนุมัติ'),
    ]
    
    quantity = models.IntegerField(default=0, null=True, blank=True)
    total_cost = models.FloatField(default=0, null=True, blank=True)
    ordered_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ผู้สั่ง")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สั่ง")
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField(blank=True, verbose_name="หมายเหตุ")
    
    # เพิ่ม fields ใหม่
    delivery_round = models.ForeignKey(
        DeliveryRound, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="รอบจัดส่ง"
    )
    approval_status = models.CharField(
        max_length=20, 
        choices=APPROVAL_STATUS_CHOICES, 
        default='pending',
        verbose_name="สถานะอนุมัติ"
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_orders',
        verbose_name="ผู้อนุมัติ"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="วันที่อนุมัติ")

    class Meta:
        verbose_name = "รายการสั่งซื้อ"
        verbose_name_plural = "รายการสั่งซื้อ"
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} by {self.ordered_by.username}"

    def get_status_display_badge(self):
        """สำหรับแสดงสถานะในรูปแบบ badge"""
        status_badges = {
            'pending': 'badge bg-warning',
            'approved': 'badge bg-success',
            'rejected': 'badge bg-danger',
        }
        return status_badges.get(self.approval_status, 'badge bg-secondary')


class MaterialOrderItem(models.Model):
    order = models.ForeignKey(MaterialOrder, related_name='items', on_delete=models.CASCADE)
    material = models.ForeignKey(MaterialStock, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.FloatField()
    total_cost = models.FloatField()

    def __str__(self):
        return f"{self.material.name} x {self.quantity}"