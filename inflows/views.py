from rest_framework import generics
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from . import models, forms, serializers
from app.demo import DemoAPIViewMixin, DemoDeleteSimulationMixin, DemoWriteSimulationMixin


class InflowListView(ListView):
    model = models.Inflow
    template_name = 'inflow_list.html'
    context_object_name = 'inflows'
    paginate_by = 5
    permission_required = 'inflows.view_inflow'

    def get_queryset(self):
        queryset = super().get_queryset()
        product = self.request.GET.get('product')

        if product:
            queryset = queryset.filter(product__title__icontains=product)
        return queryset


class InflowCreateView(DemoWriteSimulationMixin, CreateView):
    model = models.Inflow
    template_name = 'inflow_create.html'
    form_class = forms.InflowForm
    success_url = reverse_lazy('inflow_list')
    permission_required = 'inflows.add_inflow'




class InflowUpdateView(DemoWriteSimulationMixin, UpdateView):
    model = models.Inflow
    form_class = forms.InflowForm
    template_name = 'inflow_update.html'
    success_url = reverse_lazy('inflow_list')


class InflowDeleteView(DemoDeleteSimulationMixin, DeleteView):
    model = models.Inflow
    template_name = 'inflow_delete.html'
    success_url = reverse_lazy('inflow_list')

class InflowDetailView(DetailView):
    model = models.Inflow
    template_name = 'inflow_detail.html'
    permission_required = 'inflows.view_inflow'


class InflowCreateListAPIView(DemoAPIViewMixin, generics.ListCreateAPIView):
    queryset = models.Inflow.objects.all()
    serializer_class = serializers.InflowSerializer


class InflowRetrieveAPIView(generics.RetrieveAPIView):
    queryset = models.Inflow.objects.all()
    serializer_class = serializers.InflowSerializer
