from django.core.management import call_command
from rest_framework.test import APITestCase

from catalog.models import Ward


class WardTests(APITestCase):
    def test_load_official_list_and_order(self):
        call_command("load_wards", verbosity=0)
        call_command("load_wards", verbosity=0)  # idempotent
        self.assertEqual(Ward.objects.count(), 94)
        self.assertEqual(Ward.objects.filter(kind="ward").count(), 23)
        self.assertEqual(Ward.objects.filter(kind="commune").count(), 70)
        self.assertEqual(Ward.objects.filter(kind="special_zone").count(), 1)

        res = self.client.get("/api/wards/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 94)
        # Appendix B units first (32 of them), then the rest
        priorities = [w["priority"] for w in res.data]
        self.assertEqual(priorities, sorted(priorities))
        self.assertEqual(sum(p < 100 for p in priorities), 32)
        self.assertEqual(res.data[0]["priority"], 1)
        labels = {w["label"] for w in res.data}
        for name in ["Xã Đại Lộc", "Phường Hội An", "Xã Tam Hải", "Xã Tân Hiệp", "Đặc khu Hoàng Sa",
                     "Xã Avương"]:
            self.assertIn(name, labels)

    def test_search(self):
        call_command("load_wards", verbosity=0)
        res = self.client.get("/api/wards/", {"search": "hội an"})
        self.assertEqual({w["name"] for w in res.data}, {"Hội An", "Hội An Đông", "Hội An Tây"})
        res = self.client.get("/api/wards/", {"search": "dai loc"})  # without diacritics
        self.assertEqual([w["name"] for w in res.data], ["Đại Lộc"])
