"""Criterion a: the base-data command and load_history can run twice without duplicating."""
from alerts.models import Alert
from catalog.models import Ward
from reservoirs.models import (OperatingDirective, OperationRecord, Rainfall, RegulatoryThreshold,
                               Reservoir, ReservoirWard)

from .helpers import HOURS, ReservoirTestCase


def counts():
    return {m.__name__: m.objects.count() for m in (
        Reservoir, RegulatoryThreshold, OperatingDirective, ReservoirWard, OperationRecord,
        Rainfall, Ward, Alert)}


class LoadCommandTests(ReservoirTestCase):
    def test_second_run_duplicates_nothing(self):
        first = counts()
        self.assertEqual(first["Reservoir"], 4)
        self.assertEqual(first["RegulatoryThreshold"], 16)
        self.assertEqual(first["OperatingDirective"], 9)
        self.assertEqual(first["ReservoirWard"], 72)
        self.assertEqual(first["OperationRecord"], 4 * HOURS)
        self.assertEqual(first["Rainfall"], 4 * HOURS)
        values = list(OperationRecord.objects.order_by("reservoir", "time")
                      .values_list("water_level", "inflow", "suspicious"))

        self.run_command("load_reservoirs")
        self.run_command("load_history")
        self.assertEqual(counts(), first)
        self.assertEqual(list(OperationRecord.objects.order_by("reservoir", "time")
                              .values_list("water_level", "inflow", "suspicious")), values)

    def test_base_data_matches_appendix(self):
        av = Reservoir.objects.get(code="av")
        self.assertEqual([r.normal_water_level for r in Reservoir.objects.all()],
                         [380.0, 258.0, 222.5, 175.0])
        t = RegulatoryThreshold.objects.get(reservoir=av, kind="max_before_flood", start_day="11-16")
        self.assertEqual((t.end_day, t.value_low, t.value_high), ("12-15", 377.0, 380.0))
        self.assertFalse(OperatingDirective.objects.filter(is_active=True).exists())
        starred = ReservoirWard.objects.filter(reservoir=av, needs_verification=True)
        self.assertEqual(sorted(link.ward.name for link in starred),
                         ["Sông Kôn", "Sông Vàng", "Đông Giang"])
        self.assertIn("Mọi tên trong Phụ lục B đều khớp", self.run_command("load_reservoirs"))
