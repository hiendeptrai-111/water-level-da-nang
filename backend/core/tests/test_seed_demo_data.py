"""seed_demo_data: refuses to run outside development."""
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import User


class SeedDemoDataTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuses_when_debug_is_false(self):
        with self.assertRaisesMessage(CommandError, "TỪ CHỐI"):
            call_command("seed_demo_data")
        self.assertFalse(User.objects.filter(email__endswith="@demo.example.com").exists())
