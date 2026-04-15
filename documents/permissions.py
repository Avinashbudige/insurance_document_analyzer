from rest_framework import permissions

class IsDocumentOwner(permissions.BasePermission):
    """Permission to only allow owners of a document to access it"""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user
        
        # Write permissions are only allowed to the owner
        return obj.user == request.user