from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import *
from django.contrib.auth.models import User
import pandas as pd
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import *
from django.contrib.auth.models import User
import pandas as pd
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q

@login_required
def home(request):
    orders = MaterialOrder.objects.all().order_by('-created_at')
    filter_order = []
    all_cost = []

    admin_list = ['admin','admin2','area_manager','coo','ceo']

    for o in orders:
        print('USER: ', [o.ordered_by,request.user.username])
        if request.user.username in admin_list:
            filter_order.append(o)
            all_cost.append(o.total_cost)
        elif o.ordered_by.username == request.user.username:
            filter_order.append(o)
            all_cost.append(o.total_cost)
    
    sumtotal = len(filter_order)
    total_cost = sum(all_cost)
    print(sumtotal,total_cost)
    
    # นับจำนวนตามสถานะ
    status_counts = MaterialOrder.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(approval_status='pending')),
        approved=Count('id', filter=Q(approval_status='approved')),
        rejected=Count('id', filter=Q(approval_status='rejected'))
    )
    # {% if order.ordered_by.username == request.user.username %}
    return render(request, 'inventory/home.html', {
        'orders': filter_order,
        'status_counts': status_counts,
        'total_order': sumtotal,
        'total_cost': total_cost
    })



# หน้าอัปโหลด Excel
@login_required
def import_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        df = pd.read_excel(request.FILES['excel_file'])

        for _, row in df.iterrows():
            def safe_value(val, default='-'):
                if pd.isna(val):
                    return default
                return val

            MaterialStock.objects.update_or_create(
                code=safe_value(row['รหัสสินค้า']),
                defaults={
                    'name': safe_value(row['ชื่อสินค้า']),
                    'barcode': safe_value(row['Barcode']),
                    'cost': safe_value(row['ต้นทุน'], 0.0),
                    'avg_cost': safe_value(row['ต้นทุนเฉลี่ย'], 0.0),
                    'unit': safe_value(row['หน่วยนับ']),
                    'sale_price': safe_value(row['ราคาขายสำหรับสาขา'], 0.0),
                    'reorder_point': safe_value(row['จุดสั่งซื้อ'], 0),
                    'max_stock': safe_value(row['จุดสูงสุด'], 0),
                    'category': safe_value(row['ประเภทสินค้า']),
                }
            )
        return redirect('material_list')
    return render(request, 'inventory/import_excel.html')


# รายการสต็อก
@login_required
def material_list(request):
    materials = MaterialStock.objects.all()
    return render(request, 'inventory/material_list.html', {'materials': materials})

# หน้าออร์เดอร์สินค้า
@login_required
def order_material(request):
    # 1-ปุ่มอนุมัติการสังซื้อ (user: area_manager)
    # 2-รอบส่ง (รอบส่ง-หาดใหญ่-จันทร์ 2 มิถุนายน) (คนเพิ่มรอบส่ง: perchase_manager)
    # 
    if request.method == 'POST':
        note = request.POST.get('note', '')
        material_ids = request.POST.getlist('material_id')
        qtys = request.POST.getlist('qty')
        costs = request.POST.getlist('cost')

        print(f"Material IDs: {material_ids}")
        print(f"Quantities: {qtys}")
        print(f"Costs: {costs}")

        # ตรวจสอบว่ามีข้อมูลหรือไม่
        if not material_ids:
            return redirect('order_material')

        # สร้าง order โดยไม่ต้องใส่ material (ถ้าใช้วิธี migration)
        order = MaterialOrder.objects.create(
            ordered_by=request.user,
            note=note,
            created_at=timezone.now(),
            total_cost=0
        )

        print('Order created successfully')

        total_cost = 0
        for mid, qty, cost in zip(material_ids, qtys, costs):
            try:
                if not mid or not qty or not cost:
                    continue  # ข้ามถ้าข้อมูลว่าง

                mid = int(mid)
                quantity = int(qty)
                cost_value = float(cost)

                material = MaterialStock.objects.get(pk=mid)
                item_total = quantity * cost_value

                MaterialOrderItem.objects.create(
                    order=order,
                    material=material,
                    quantity=quantity,
                    unit_cost=cost_value,
                    total_cost=item_total
                )
                total_cost += item_total

            except (ValueError, MaterialStock.DoesNotExist):
                continue  # ข้ามรายการที่ผิดพลาด

        order.total_cost = total_cost
        order.save()
        return redirect('home')

    today = timezone.now()
    next_id = MaterialOrder.objects.count() + 1
    return render(request, 'inventory/order_form.html', {
        'today': today,
        'order_id': f"{next_id:05d}"
    })

# ค้นหาสินค้าแบบ real-time
@login_required
def search_materials(request):
    query = request.GET.get('q', '')
    results = MaterialStock.objects.filter(name__icontains=query)[:10]  # จำกัด 10 รายการ
    data = [
        {
            'id': m.id,
            'code': m.code,
            'name': m.name,
            'cost': m.cost
        }
        for m in results
    ]
    return JsonResponse(data, safe=False)


# dashboard
@login_required
def dashboard(request):
    materials = MaterialStock.objects.all()
    orders = MaterialOrder.objects.all()
    return render(request, 'inventory/dashboard.html', {'stocks': materials, 'orders': orders})


@login_required
def material_create(request):
    if request.method == 'POST':
        MaterialStock.objects.create(
            code=request.POST['code'],
            name=request.POST['name'],
            barcode=request.POST.get('barcode', ''),
            cost=request.POST.get('cost', 0),
            avg_cost=request.POST.get('avg_cost', 0),
            unit=request.POST.get('unit', ''),
            sale_price=request.POST.get('sale_price', 0),
            reorder_point=request.POST.get('reorder_point', 0),
            max_stock=request.POST.get('max_stock', 0),
            category=request.POST.get('category', '')
        )
        return redirect('material_list')
    return render(request, 'inventory/material_form.html', {'title': 'เพิ่มวัตถุดิบ'})

@login_required
def material_edit(request, pk):
    material = get_object_or_404(MaterialStock, pk=pk)
    if request.method == 'POST':
        for field in ['code', 'name', 'barcode', 'cost', 'avg_cost', 'unit', 'sale_price', 'reorder_point', 'max_stock', 'category']:
            setattr(material, field, request.POST.get(field, getattr(material, field)))
        material.save()
        return redirect('material_list')
    return render(request, 'inventory/material_form.html', {'title': 'แก้ไขวัตถุดิบ', 'material': material})

@login_required
def material_delete(request, pk):
    material = get_object_or_404(MaterialStock, pk=pk)
    if request.method == 'POST':
        material.delete()
        return redirect('material_list')
    return render(request, 'inventory/material_confirm_delete.html', {'material': material})


@login_required
def order_edit(request, pk):
    order = get_object_or_404(MaterialOrder, pk=pk)
    if request.method == 'POST':
        note = request.POST.get('note', '')
        total = 0
        for item in order.items.all():
            qty = int(request.POST.get(f'qty_{item.id}', item.quantity))
            cost = float(request.POST.get(f'cost_{item.id}', item.unit_cost))
            item.quantity = qty
            item.unit_cost = cost
            item.total_cost = qty * cost
            item.save()
            total += item.total_cost
        order.note = note
        order.total_cost = total
        order.save()
        return redirect('home')
    return render(request, 'inventory/order_edit.html', {'order': order})

@login_required
def order_delete(request, pk):
    order = get_object_or_404(MaterialOrder, pk=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('home')
    return render(request, 'inventory/order_confirm_delete.html', {'order': order})




# views.py - อัปเดต order_material view



# อัปเดต order_material view
@login_required
def order_material(request):
    if request.method == 'POST':
        note = request.POST.get('note', '')
        delivery_round_id = request.POST.get('delivery_round')
        material_ids = request.POST.getlist('material_id')
        qtys = request.POST.getlist('qty')
        costs = request.POST.getlist('cost')

        print(f"Material IDs: {material_ids}")
        print(f"Quantities: {qtys}")
        print(f"Costs: {costs}")
        print(f"Delivery Round ID: {delivery_round_id}")

        # ตรวจสอบว่ามีข้อมูลหรือไม่
        if not material_ids:
            messages.error(request, 'กรุณาเลือกวัตถุดิบอย่างน้อย 1 รายการ')
            return redirect('order_material')

        try:
            # ดึงรอบจัดส่ง
            delivery_round = None
            if delivery_round_id:
                delivery_round = DeliveryRound.objects.get(pk=delivery_round_id)

            # สร้าง order
            order = MaterialOrder.objects.create(
                ordered_by=request.user,
                note=note,
                delivery_round=delivery_round,
                total_cost=0,
                approval_status='pending'  # ตั้งค่าเริ่มต้นเป็นรออนุมัติ
            )

            print('Order created successfully')

            total_cost = 0
            items_created = 0

            for mid, qty, cost in zip(material_ids, qtys, costs):
                try:
                    if not mid or not qty or not cost:
                        continue  # ข้ามถ้าข้อมูลว่าง

                    mid = int(mid)
                    quantity = int(qty)
                    cost_value = float(cost)

                    if quantity <= 0:
                        continue

                    material = MaterialStock.objects.get(pk=mid)
                    item_total = quantity * cost_value

                    MaterialOrderItem.objects.create(
                        order=order,
                        material=material,
                        quantity=quantity,
                        unit_cost=cost_value,
                        total_cost=item_total
                    )
                    total_cost += item_total
                    items_created += 1

                except (ValueError, MaterialStock.DoesNotExist):
                    continue  # ข้ามรายการที่ผิดพลาด

            if items_created == 0:
                order.delete()
                messages.error(request, 'ไม่สามารถสร้างรายการสั่งซื้อได้')
                return redirect('order_material')

            order.total_cost = total_cost
            order.save()
            
            messages.success(request, f'สร้างรายการสั่งซื้อ MOD-{order.id:05d} เรียบร้อยแล้ว (สถานะ: รออนุมัติ)')
            return redirect('home')

        except DeliveryRound.DoesNotExist:
            messages.error(request, 'ไม่พบรอบจัดส่งที่เลือก')
            return redirect('order_material')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            return redirect('order_material')

    # ดึงข้อมูลรอบจัดส่งที่เปิดใช้งาน
    delivery_rounds = DeliveryRound.objects.filter(is_active=True).order_by('name')
    
    today = timezone.now()
    next_id = MaterialOrder.objects.count() + 1
    return render(request, 'inventory/order_form.html', {
        'today': today,
        'order_id': f"{next_id:05d}",
        'delivery_rounds': delivery_rounds
    })