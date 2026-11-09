from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Doar proprietarul obiectului îl poate modifica. Funcționează pentru
    recenzii, comentarii (user), citate (created_by_user) și liste (owner_user)."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        for attr in ("user_id", "created_by_user_id", "owner_user_id"):
            if hasattr(obj, attr):
                return getattr(obj, attr) == request.user.id
        return False