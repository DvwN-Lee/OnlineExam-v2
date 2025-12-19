"""
Custom permission classes for role-based access control.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTeacher(BasePermission):
    """
    Permission class that allows access only to teachers.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'user_type')
            and request.user.user_type == 'teacher'
        )


class IsStudent(BasePermission):
    """
    Permission class that allows access only to students.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'user_type')
            and request.user.user_type == 'student'
        )


class IsOwnerOrTeacher(BasePermission):
    """
    Permission class that allows access to:
    - Teachers (full access)
    - Object owners (full access to their own objects)
    - Others (read-only access)
    """

    def has_object_permission(self, request, view, obj):
        # Teachers have full access
        if request.user.user_type == 'teacher':
            return True

        # Read permissions are allowed to any authenticated user
        if request.method in SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'create_user'):
            return obj.create_user == request.user

        return False


class IsExamCreator(BasePermission):
    """
    Permission class that allows access only to the exam creator.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator
        return obj.create_user == request.user


class IsQuestionOwner(BasePermission):
    """
    Permission class for question management.
    - Teachers can create questions
    - Only question creator can modify/delete
    - Students can only view shared questions
    """

    def has_permission(self, request, view):
        # Allow list/retrieve for all authenticated users
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated

        # Only teachers can create questions
        return (
            request.user.is_authenticated
            and request.user.user_type == 'teacher'
        )

    def has_object_permission(self, request, view, obj):
        # Allow read access based on share status
        if request.method in SAFE_METHODS:
            if request.user.user_type == 'teacher':
                return True
            # Students can only view shared questions
            return obj.is_share and not obj.is_del

        # Only the creator can modify/delete
        return obj.create_user == request.user
