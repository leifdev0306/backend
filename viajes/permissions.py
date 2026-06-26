from rest_framework import permissions

class IsEntidadOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'entidad'):
            return obj.entidad.user == request.user
        if hasattr(obj, 'viaje') and hasattr(obj.viaje, 'entidad'):
            return obj.viaje.entidad.user == request.user
        return False

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser