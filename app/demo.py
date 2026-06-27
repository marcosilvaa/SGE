from django.contrib import messages
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.response import Response

DEMO_MESSAGE = "Modo demonstração: ação simulada. Nenhuma alteração foi salva."


class DemoSuccessURLMixin:
    """Resolve success_url without requiring an unsaved self.object."""

    def get_demo_success_url(self):
        success_url = getattr(self, "success_url", None)
        if success_url:
            return str(success_url)
        return self.get_success_url()


class DemoWriteSimulationMixin(DemoSuccessURLMixin):
    """Simulate successful form writes without mutating the database."""

    def form_valid(self, form):
        messages.info(self.request, DEMO_MESSAGE)
        return redirect(self.get_demo_success_url())


class DemoDeleteSimulationMixin(DemoSuccessURLMixin):
    """Simulate successful deletes without mutating the database."""

    def form_valid(self, form):
        messages.info(self.request, DEMO_MESSAGE)
        return redirect(self.get_demo_success_url())


class DemoAPIViewMixin:
    """Return successful API write responses without mutating the database."""

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": DEMO_MESSAGE}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": DEMO_MESSAGE}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        self.get_object()
        return Response({"detail": DEMO_MESSAGE}, status=status.HTTP_200_OK)
