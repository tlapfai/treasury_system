from django.test import TestCase
from swpm.models import *
import QuantLib as ql

class FXOTestCase(TestCase):

    def setUp(self):

        cdr_uk = Calendar.objects.create(name='UnitedKingdom')
        cdr_hk = Calendar.objects.create(name='HongKong')

        # Create airports.
        a1 = Ccy.objects.create(code="HKD", cdr=cdr_hk)
        a2 = Ccy.objects.create(code="CNH", cdr=cdr_hk)
        cp = CcyPair.objects.create(base_ccy=a1, quote_ccy=a2, cdr=cdr_hk)

        # Create flights.
        Flight.objects.create(origin=a1, destination=a2, duration=100)


    def test_departures_count(self):
        a = Airport.objects.get(code="AAA")
        self.assertEqual(a.departures.count(), 3)