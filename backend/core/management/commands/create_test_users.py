"""
Management command to create test users with different roles.

Creates three users with their associated Staff profiles:
- admin user (role: admin)
- manager user (role: manager)
- staff user (role: staff)

Usage:
    python manage.py create_test_users
    python manage.py create_test_users --reset  # Delete existing test users first
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Staff


class Command(BaseCommand):
    help = "Create test users with admin, manager, and staff roles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing test users before creating new ones",
        )

    def handle(self, *args, **options):
        reset = options.get("reset", False)

        test_users = [
            {
                "username": "admin",
                "password": "admin123",
                "email": "admin@taskroot.local",
                "first_name": "Admin",
                "last_name": "User",
                "role": "admin",
            },
            {
                "username": "manager",
                "password": "manager123",
                "email": "manager@taskroot.local",
                "first_name": "Manager",
                "last_name": "User",
                "role": "manager",
            },
            {
                "username": "staff",
                "password": "staff123",
                "email": "staff@taskroot.local",
                "first_name": "Staff",
                "last_name": "User",
                "role": "staff",
            },
        ]

        if reset:
            self.stdout.write(self.style.WARNING("Deleting existing test users..."))
            for user_data in test_users:
                try:
                    user = User.objects.get(username=user_data["username"])
                    # Delete associated Staff profile if exists
                    if hasattr(user, "staff"):
                        user.staff.delete()
                    user.delete()
                    self.stdout.write(self.style.SUCCESS(f"  Deleted user: {user_data['username']}"))
                except User.DoesNotExist:
                    pass

        self.stdout.write(self.style.SUCCESS("Creating test users..."))

        for user_data in test_users:
            try:
                with transaction.atomic():
                    # Create Django user
                    user, created = User.objects.get_or_create(
                        username=user_data["username"],
                        defaults={"email": user_data["email"]},
                    )

                    if created:
                        user.set_password(user_data["password"])
                        user.save()
                        self.stdout.write(self.style.SUCCESS(f"  Created user: {user_data['username']}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  User already exists: {user_data['username']}"))

                    # Create Staff profile
                    staff, staff_created = Staff.objects.get_or_create(
                        user=user,
                        defaults={
                            "email": user_data["email"],
                            "first_name": user_data["first_name"],
                            "last_name": user_data["last_name"],
                            "role": user_data["role"],
                            "status": "active",
                        },
                    )

                    if staff_created:
                        self.stdout.write(self.style.SUCCESS(f"    Created Staff profile: {user_data['role']}"))
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"    Staff profile already exists for: {user_data['username']}")
                        )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error creating {user_data['username']}: {str(e)}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✓ Test users created successfully!"))
        self.stdout.write("")
        self.stdout.write("You can now use these credentials:")
        self.stdout.write("  Admin:   username=admin,   password=admin123")
        self.stdout.write("  Manager: username=manager, password=manager123")
        self.stdout.write("  Staff:   username=staff,   password=staff123")
