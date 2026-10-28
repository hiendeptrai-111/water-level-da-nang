"""Phase 4 criteria a–l: SOS, claims, flood points and routing, history, privacy, permissions."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

import networkx as nx
from django.core.management import call_command
from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import BaseAPITestCase
from catalog.models import RescueTeam, Ward
from core.models import SystemConfig
from rescue import routing, services
from rescue.models import SOS, FloodPoint, SOSHistory

# Around the centre of Xã Đại Lộc (a real commune boundary, so the ward is inferred).
LAT, LON = 15.8991, 108.1032


def small_graph():
    """A -> B -> C (short, through B) and A -> D -> C (long detour). Two-way edges."""
    G = nx.MultiDiGraph(crs="epsg:4326")
    pts = {"A": (LAT, LON - 0.02), "B": (LAT, LON - 0.01), "C": (LAT, LON), "D": (LAT + 0.02, LON - 0.01)}
    for i, (name, (y, x)) in enumerate(pts.items(), 1):
        G.add_node(i, y=y, x=x, name=name)
    ids = {name: i for i, name in enumerate(pts, 1)}

    def road(a, b, length):
        for u, v in ((a, b), (b, a)):
            G.add_edge(ids[u], ids[v], length=length, highway="secondary")
    road("A", "B", 1070)
    road("B", "C", 1070)
    road("A", "D", 3000)
    road("D", "C", 3000)
    return G, pts


class RescueTestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        call_command("load_wards", verbosity=0)
        call_command("load_ward_centroids", verbosity=0)
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.team2 = RescueTeam.objects.create(name="Đội 2", phone_number="0905222333", vehicles=["motorbike"])
        self.rescue = self.make_user("doi@example.com", "0933333333", role=User.Role.RESCUE_TEAM)
        self.rescue2 = self.make_user("doi2@example.com", "0944444444", role=User.Role.RESCUE_TEAM,
                                      rescue_team=self.team2)
        self.citizen = self.make_user()
        G, self.pts = small_graph()
        routing.set_graph(G)
        self.addCleanup(routing.set_graph, None)
        for team, key in ((self.team, "A"), (self.team2, "A")):
            team.base_latitude, team.base_longitude = (Decimal(str(round(v, 6))) for v in self.pts[key])
            team.vehicles = ["motorbike"]
            team.save()

    def send(self, phone="0987654321", **extra):
        body = {"latitude": LAT, "longitude": LON, "accuracy_m": 12, **({"phone": phone} if phone else {}), **extra}
        return self.client.post("/api/sos/", body, format="json")

    def age(self, sos, minutes):
        SOS.objects.filter(pk=sos.pk).update(created_at=timezone.now() - timedelta(minutes=minutes))
        sos.refresh_from_db()


class SubmitTests(RescueTestCase):
    # a.
    def test_anonymous_needs_phone(self):
        res = self.send(phone=None)
        self.assertEqual(res.status_code, 400)
        self.assertIn("phone", res.data)
        ok = self.send()
        self.assertEqual(ok.status_code, 201, ok.data)
        sos = SOS.objects.get(code=ok.data["code"])
        self.assertEqual(sos.ward.name, "Đại Lộc")             # inferred from the boundary
        self.assertEqual(sos.status, SOS.Status.NEW)

    def test_citizen_phone_filled_from_profile(self):
        self.auth(self.citizen)
        res = self.send(phone=None)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(SOS.objects.get().phone, self.citizen.phone_number)

    # b.
    def test_second_sos_updates_the_open_one(self):
        first = self.send().data["code"]
        res = self.send(latitude=LAT + 0.001)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["created"])
        self.assertEqual(res.data["code"], first)
        self.assertEqual(SOS.objects.count(), 1)
        self.assertEqual(SOS.objects.get().latitude, Decimal(str(LAT + 0.001)).quantize(Decimal("0.000001")))

    # c.
    def test_rate_limited_by_ip_and_device(self):
        SystemConfig.objects.filter(key="sos_rate_limit_per_hour").update(value=2)
        self.assertEqual(self.send(phone="0911000001").status_code, 201)
        self.assertEqual(self.send(phone="0911000002").status_code, 201)
        self.assertEqual(self.send(phone="0911000003").status_code, 429)

    def test_supplement_and_cancel_with_code_and_phone(self):
        code = self.send().data["code"]
        res = self.client.patch(f"/api/sos/{code}/", {"phone": "0987654321", "people_count": "5+",
                                                      "vulnerable_groups": ["elderly", "child"],
                                                      "water_level": "roof"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        sos = SOS.objects.get(code=code)
        self.assertGreater(sos.priority_score, 90)
        self.assertEqual(self.client.get(f"/api/sos/{code}/?phone=0999999999").status_code, 404)
        self.assertEqual(self.client.post(f"/api/sos/{code}/cancel/", {"phone": "0987654321"},
                                          format="json").status_code, 200)
        self.assertEqual(SOS.objects.get(code=code).status, SOS.Status.CANCELLED)

    # l.
    def test_routing_failure_never_blocks_sending(self):
        with mock.patch.object(routing, "load_graph", side_effect=RuntimeError("đồ thị hỏng")):
            res = self.send()
            self.assertEqual(res.status_code, 201)
            sos = SOS.objects.get(code=res.data["code"])
            self.auth(self.admin)
            assign = self.client.post(f"/api/dispatch/sos/{sos.pk}/assign/", {"team": self.team.pk}, format="json")
            self.assertEqual(assign.status_code, 200)               # assigned, just without a route
            self.assertEqual(assign.data["route"], [])
            sugg = self.client.get(f"/api/dispatch/sos/{sos.pk}/suggestions/")
            self.assertEqual(sugg.status_code, 200)
            self.assertIn("Không tính được tuyến đường", sugg.data["error"])


class TeamTests(RescueTestCase):
    def setUp(self):
        super().setUp()
        self.sos = SOS.objects.get(code=self.send().data["code"])

    def tasks(self, user):
        self.auth(user)
        res = self.client.get("/api/rescue/tasks/")
        self.assertEqual(res.status_code, 200)
        return res.data

    # e.
    def test_claimable_only_after_wait(self):
        self.age(self.sos, 14)
        self.assertEqual(self.tasks(self.rescue)["claimable"], [])
        self.assertEqual(self.client.post(f"/api/rescue/tasks/{self.sos.pk}/claim/").status_code, 409)
        self.age(self.sos, 16)
        self.assertEqual([s["code"] for s in self.tasks(self.rescue)["claimable"]], [self.sos.code])

    # d.
    def test_phone_hidden_until_claimed(self):
        self.age(self.sos, 16)
        data = self.tasks(self.rescue)
        self.assertNotIn("phone", data["claimable"][0])
        self.assertNotIn(self.sos.phone, str(data))
        res = self.client.post(f"/api/rescue/tasks/{self.sos.pk}/claim/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["phone"], self.sos.phone)
        assigned = self.tasks(self.rescue)["assigned"]
        self.assertEqual(assigned[0]["phone"], self.sos.phone)
        self.assertGreater(assigned[0]["eta_seconds"], 0)
        # the other team still never sees it
        self.assertNotIn(self.sos.phone, str(self.tasks(self.rescue2)))

    # f.
    def test_two_teams_claim_only_one_wins(self):
        self.age(self.sos, 20)
        self.auth(self.rescue)
        first = self.client.post(f"/api/rescue/tasks/{self.sos.pk}/claim/")
        self.auth(self.rescue2)
        second = self.client.post(f"/api/rescue/tasks/{self.sos.pk}/claim/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.sos.refresh_from_db()
        self.assertEqual(self.sos.team, self.team)
        self.team.refresh_from_db()
        self.assertEqual(self.team.status, RescueTeam.Status.BUSY)

    def test_busy_team_cannot_claim(self):
        other = SOS.objects.get(code=self.send(phone="0911000009").data["code"])
        for s in (self.sos, other):
            self.age(s, 20)
        self.auth(self.rescue)
        self.assertEqual(self.client.post(f"/api/rescue/tasks/{self.sos.pk}/claim/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/rescue/tasks/{other.pk}/claim/").status_code, 409)

    def test_waiting_sos_notifies_nearest_teams_once(self):
        self.age(self.sos, 16)
        self.assertEqual(services.notify_claimable(), [self.sos.code])
        self.assertEqual(services.notify_claimable(), [])
        self.assertTrue(self.rescue.notifications.filter(sos=self.sos, channel="web").exists())


class RoutingTests(RescueTestCase):
    def setUp(self):
        super().setUp()
        self.sos = SOS.objects.get(code=self.send().data["code"])
        self.mid = self.pts["B"]

    def eta(self):
        return services.suggest(self.sos, teams=[self.team], limit=1)[0]

    def flood(self, level, status=FloodPoint.Status.APPROVED, at=None):
        lat, lon = at or self.mid
        return FloodPoint.objects.create(latitude=Decimal(str(round(lat, 6))), longitude=Decimal(str(round(lon, 6))),
                                         level=level, status=status,
                                         expires_at=timezone.now() + timedelta(hours=12))

    # g.
    def test_no_car_flood_blocks_the_short_road(self):
        base = self.eta()
        self.assertEqual(base.mode, "road")
        self.flood("no_car")
        detour = self.eta()
        self.assertGreater(detour.seconds, base.seconds * 2)
        self.flood("boat_only", at=self.pts["D"])
        blocked = self.eta()
        self.assertEqual(blocked.mode, "none")
        self.assertIsNone(blocked.seconds)
        self.assertEqual(blocked.note, "Không tiếp cận được bằng đường bộ")

    def test_no_motorbike_slows_down(self):
        base = self.eta()
        self.flood("no_motorbike")
        slowed = self.eta()
        self.assertGreater(slowed.seconds, base.seconds)

    def test_boat_team_uses_straight_line(self):
        self.flood("boat_only")
        self.flood("boat_only", at=self.pts["D"])
        self.team.vehicles = ["boat"]
        self.team.save()
        r = self.eta()
        self.assertEqual(r.mode, "boat")
        expected = routing.haversine_m(*self.pts["A"], LAT, LON) / (20 / 3.6)
        self.assertAlmostEqual(r.seconds, expected, delta=1)

    # h.
    def test_pending_or_expired_flood_points_change_nothing(self):
        base = self.eta().seconds
        self.flood("no_car", status=FloodPoint.Status.PENDING)
        self.assertEqual(self.eta().seconds, base)
        old = self.flood("no_car")
        FloodPoint.objects.filter(pk=old.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.eta().seconds, base)


class LifecycleTests(RescueTestCase):
    # i.
    def test_every_status_change_has_a_history_row(self):
        sos = SOS.objects.get(code=self.send().data["code"])
        self.auth(self.admin)
        self.assertEqual(self.client.post(f"/api/dispatch/sos/{sos.pk}/receive/").status_code, 200)
        sugg = self.client.get(f"/api/dispatch/sos/{sos.pk}/suggestions/").data["suggestions"]
        self.assertEqual(len(sugg), 2)
        self.assertEqual(self.client.post(f"/api/dispatch/sos/{sos.pk}/assign/", {"team": self.team.pk},
                                          format="json").status_code, 200)
        self.auth(self.rescue)
        for action in ("arrived", "rescued"):
            self.assertEqual(self.client.post(f"/api/rescue/tasks/{sos.pk}/{action}/").status_code, 200)
        self.auth(self.admin)
        self.assertEqual(self.client.post(f"/api/dispatch/sos/{sos.pk}/close/").status_code, 200)
        changes = [(h.from_status, h.to_status) for h in SOSHistory.objects.filter(sos=sos)
                   if h.from_status != h.to_status]
        self.assertEqual(changes, [("", "new"), ("new", "received"), ("received", "moving"),
                                   ("moving", "rescued"), ("rescued", "closed")])
        self.team.refresh_from_db()
        self.assertEqual(self.team.status, RescueTeam.Status.AVAILABLE)

    def test_receive_lock_between_admins(self):
        other = self.make_user("admin2@example.com", "0955555555", role=User.Role.ADMIN)
        sos = SOS.objects.get(code=self.send().data["code"])
        self.auth(self.admin)
        self.assertEqual(self.client.post(f"/api/dispatch/sos/{sos.pk}/receive/").status_code, 200)
        self.auth(other)
        self.assertEqual(self.client.post(f"/api/dispatch/sos/{sos.pk}/receive/").status_code, 409)

    def test_merge_and_return(self):
        a = SOS.objects.get(code=self.send().data["code"])
        b = SOS.objects.get(code=self.send(phone="0911000008").data["code"])
        self.auth(self.admin)
        self.assertEqual(self.client.post(f"/api/dispatch/sos/{b.pk}/merge/", {"into": a.code},
                                          format="json").status_code, 200)
        b.refresh_from_db()
        self.assertEqual((b.status, b.merged_into), (SOS.Status.CLOSED, a))
        self.client.post(f"/api/dispatch/sos/{a.pk}/assign/", {"team": self.team.pk}, format="json")
        self.auth(self.rescue)
        self.assertEqual(self.client.post(f"/api/rescue/tasks/{a.pk}/return/").status_code, 409)   # reason needed
        self.assertEqual(self.client.post(f"/api/rescue/tasks/{a.pk}/return/", {"note": "Xe hỏng"},
                                          format="json").status_code, 200)
        a.refresh_from_db()
        self.assertEqual((a.status, a.team), (SOS.Status.RECEIVED, None))

    # j.
    def test_anonymize_keeps_statistics(self):
        sos = SOS.objects.get(code=self.send(people_count="2-4").data["code"])
        services.supplement(sos, {"people_count": "2-4", "water_level": "chest", "note": "Nhà số 5"})
        self.auth(self.admin)
        self.client.post(f"/api/dispatch/sos/{sos.pk}/close/")
        SOS.objects.filter(pk=sos.pk).update(finished_at=timezone.now() - timedelta(days=91))
        call_command("anonymize_sos", stdout=open("/dev/null", "w"))
        sos.refresh_from_db()
        ward = Ward.objects.get(kind="commune", name="Đại Lộc")
        self.assertEqual((sos.phone, sos.note, bool(sos.photo), sos.sender, sos.ip_address),
                         ("", "", False, None, None))
        self.assertEqual((sos.latitude, sos.longitude), (ward.latitude, ward.longitude))
        self.assertIsNotNone(sos.anonymized_at)
        self.assertEqual((sos.ward, sos.status, sos.people_count, sos.water_level),
                         (ward, SOS.Status.CLOSED, "2-4", "chest"))
        self.assertTrue(sos.history.exists())
        self.client.credentials()                                  # admins do not send SOS
        recent = SOS.objects.get(code=self.send(phone="0911000007").data["code"])
        services.close(recent.pk, self.admin)
        services.anonymize()
        recent.refresh_from_db()
        self.assertEqual(recent.phone, "0911000007")             # not old enough yet


class PermissionTests(RescueTestCase):
    # k.
    def test_citizen_gets_403_on_dispatch(self):
        sos = SOS.objects.get(code=self.send().data["code"])
        self.auth(self.citizen)
        for method, url in (("get", "/api/dispatch/sos/"), ("get", f"/api/dispatch/sos/{sos.pk}/"),
                            ("get", f"/api/dispatch/sos/{sos.pk}/suggestions/"),
                            ("post", f"/api/dispatch/sos/{sos.pk}/receive/"),
                            ("post", f"/api/dispatch/sos/{sos.pk}/assign/"),
                            ("get", "/api/admin/flood-points/"), ("get", "/api/rescue/tasks/")):
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url, {"team": self.team.pk}, format="json").status_code, 403)

    def test_rescue_team_cannot_assign(self):
        sos = SOS.objects.get(code=self.send().data["code"])
        self.auth(self.rescue)
        res = self.client.post(f"/api/dispatch/sos/{sos.pk}/assign/", {"team": self.team.pk}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.client.get("/api/dispatch/sos/").status_code, 403)
        sos.refresh_from_db()
        self.assertIsNone(sos.team)

    def test_flood_points_resident_pending_team_approved_public_anonymous(self):
        self.auth(self.citizen)
        res = self.client.post("/api/flood-points/", {"latitude": LAT, "longitude": LON, "level": "no_car"}, format="json")
        self.assertEqual(res.data["status"], "pending")
        self.auth(self.rescue)
        res = self.client.post("/api/flood-points/", {"latitude": LAT, "longitude": LON, "level": "no_car"}, format="json")
        self.assertEqual(res.data["status"], "approved")
        self.client.credentials()
        public = self.client.get("/api/flood-points/").json()
        self.assertEqual(len(public), 1)
        self.assertNotIn("reporter", public[0])
        self.assertNotIn(self.rescue.email, str(public))
