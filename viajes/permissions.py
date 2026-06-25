from rest_framework import permissions

class IsGestor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'gestor')

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff

class IsGestorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            hasattr(request.user, 'gestor') or request.user.is_staff
        )

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(request.user, 'gestor'):
            if hasattr(obj, 'entidad'):
                return obj.entidad == request.user.gestor.entidad
            if hasattr(obj, 'viaje') and hasattr(obj.viaje, 'entidad'):
                return obj.viaje.entidad == request.user.gestor.entidad
        return False