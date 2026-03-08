import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Initialize development database schema and default dev admin user"

    def handle(self, *args, **options):
        self.stdout.write("[dev-init] migrate start")
        call_command("migrate", interactive=False)
        self.stdout.write("[dev-init] migrate done")

        username = "hedgehog"
        password = os.getenv("DEV_ADMIN_PASSWORD", "hedgehog123")
        user_model = get_user_model()

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": "hedgehog@local.dev",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(f"[dev-init] dev admin created username={username}")
        else:
            self.stdout.write("[dev-init] dev admin exists")

        self.stdout.write(
            f"[dev-init] db_engine={getattr(settings, 'DB_RUNTIME_ENGINE', 'unknown')} username={username}"
        )
