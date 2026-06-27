from django.urls import reverse_lazy
from rest_framework import generics
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from . import models, forms, serializers
from app.demo import DemoAPIViewMixin, DemoDeleteSimulationMixin, DemoWriteSimulationMixin


class SupplierListView(ListView):
    model = models.Supplier
    template_name = 'supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 5
    permission_required = 'suppliers.view_supplier'

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.GET.get('name')

        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class SupplierCreateView(DemoWriteSimulationMixin, CreateView):
    model = models.Supplier
    template_name = 'supplier_create.html'
    form_class = forms.SupplierForm
    success_url = reverse_lazy('supplier_list')
    permission_required = 'suppliers.add_supplier'


class SupplierDetailView(DetailView):
    model = models.Supplier
    template_name = 'supplier_detail.html'
    permission_required = 'suppliers.view_supplier'


class SupplierUpdateView(DemoWriteSimulationMixin, UpdateView):
    model = models.Supplier
    template_name = 'supplier_update.html'
    form_class = forms.SupplierForm
    success_url = reverse_lazy('supplier_list')
    permission_required = 'suppliers.change_supplier'


class SupplierDeleteView(DemoDeleteSimulationMixin, DeleteView):
    model = models.Supplier
    template_name = 'supplier_delete.html'
    success_url = reverse_lazy('supplier_list')
    permission_required = 'suppliers.delete_supplier'


class SupplierCreateListAPIView(DemoAPIViewMixin, generics.ListCreateAPIView):
    queryset = models.Supplier.objects.all()
    serializer_class = serializers.SupplierSerializer


class SupplierRetrieveUpdateDestroyAPIView(DemoAPIViewMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Supplier.objects.all()
    serializer_class = serializers.SupplierSerializer
