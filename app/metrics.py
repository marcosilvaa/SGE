from django.db.models import Sum, F
from django.utils.formats import number_format
from django.utils import timezone
from brands.models import Brand
from categories.models import Category
from inflows.models import Inflow
from products.models import Product
from outflows.models import Outflow
from suppliers.models import Supplier


def get_product_metrics():
    products = Product.objects.all()
    total_cost_price = sum(product.cost_price * product.quantity for product in products)
    total_selling_price = sum(product.selling_price * product.quantity for product in products)
    total_quantity = sum(product.quantity for product in products)
    total_profit = total_selling_price - total_cost_price

    return dict(
        total_cost_price=number_format(total_cost_price, decimal_pos=2, force_grouping=True),
        total_selling_price=number_format(total_selling_price, decimal_pos=2, force_grouping=True),
        total_quantity=total_quantity,
        total_profit=number_format(total_profit, decimal_pos=2, force_grouping=True),
    )


def get_sales_metrics():
    total_sales = Outflow.objects.count()
    total_products_sold = Outflow.objects.aggregate(total_products_sold=Sum('quantity'))['total_products_sold'] or 0
    total_sales_value = sum(outflow.quantity * outflow.product.selling_price for outflow in Outflow.objects.all())
    total_sales_cost = sum(outflow.quantity * outflow.product.cost_price for outflow in Outflow.objects.all())
    total_sales_profit = total_sales_value - total_sales_cost

    return dict(
        total_sales=total_sales,
        total_products_sold=total_products_sold,
        total_sales_value=number_format(total_sales_value, decimal_pos=2, force_grouping=True),
        total_sales_profit=number_format(total_sales_profit, decimal_pos=2, force_grouping=True),
    )


def get_daily_sales_data():
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    values = list()

    for date in dates:
        sales_total = Outflow.objects.filter(
            created_at__date=date
        ).aggregate(
            total_sales=Sum(F('product__selling_price') * F('quantity'))
        )['total_sales'] or 0
        values.append(float(sales_total))

    return dict(
        dates=dates,
        values=values,
    )


def get_daily_sales_quantity_data():
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    quantities = list()

    for date in dates:
        sales_quantity = Outflow.objects.filter(created_at__date=date).count()
        quantities.append(sales_quantity)

    return dict(
        dates=dates,
        values=quantities,
    )


def get_graphic_product_category_metric():
    categories = Category.objects.all()
    return {category.name: Product.objects.filter(category=category).count() for category in categories}


def get_graphic_product_brand_metric():
    brands = Brand.objects.all()
    return {brand.name: Product.objects.filter(brand=brand).count() for brand in brands}


def get_dashboard_metrics():
    products = Product.objects.all()
    total_products = products.count()
    low_stock_products = products.filter(quantity__gt=0, quantity__lte=5).count()
    out_of_stock_products = products.filter(quantity=0).count()
    inflows_count = Inflow.objects.count()
    outflows_count = Outflow.objects.count()
    total_inventory_value = sum(product.selling_price * product.quantity for product in products)
    total_inventory_cost = sum(product.cost_price * product.quantity for product in products)
    estimated_margin = total_inventory_value - total_inventory_cost

    return dict(
        total_products=total_products,
        total_categories=Category.objects.count(),
        total_brands=Brand.objects.count(),
        total_suppliers=Supplier.objects.count(),
        low_stock_products=low_stock_products,
        out_of_stock_products=out_of_stock_products,
        inflows_count=inflows_count,
        outflows_count=outflows_count,
        total_movements=inflows_count + outflows_count,
        inventory_value=number_format(total_inventory_value, decimal_pos=2, force_grouping=True),
        estimated_margin=number_format(estimated_margin, decimal_pos=2, force_grouping=True),
    )


def get_stock_status_data():
    healthy = Product.objects.filter(quantity__gt=5).count()
    low = Product.objects.filter(quantity__gt=0, quantity__lte=5).count()
    empty = Product.objects.filter(quantity=0).count()

    return dict(
        labels=['Saudável', 'Estoque baixo', 'Sem estoque'],
        values=[healthy, low, empty],
    )


def get_category_inventory_value_data():
    data = dict()
    for category in Category.objects.all():
        total = sum(product.selling_price * product.quantity for product in category.products.all())
        if total:
            data[category.name] = float(total)
    return data


def get_low_stock_products(limit=6):
    return Product.objects.filter(quantity__lte=5).select_related('category', 'brand')[:limit]


def get_recent_movements(limit=8):
    inflows = [
        dict(
            kind='Entrada',
            product=item.product.title,
            quantity=item.quantity,
            date=item.created_at,
            description=item.description or 'Reposição de estoque',
        )
        for item in Inflow.objects.select_related('product').order_by('-created_at')[:limit]
    ]
    outflows = [
        dict(
            kind='Saída',
            product=item.product.title,
            quantity=item.quantity,
            date=item.created_at,
            description=item.description or 'Venda registrada',
        )
        for item in Outflow.objects.select_related('product').order_by('-created_at')[:limit]
    ]

    return sorted(inflows + outflows, key=lambda item: item['date'], reverse=True)[:limit]
