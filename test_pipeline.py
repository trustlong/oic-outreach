"""
Unit tests for find_all_homeowners_20mi.py

Run with:
    .venv/bin/python -m unittest test_pipeline -v
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import find_all_homeowners_20mi as pipeline


class TestCentroidOfRings(unittest.TestCase):
    def test_basic_square(self):
        # Square centered at lat=10, lon=20
        geom = {"rings": [[[19, 9], [21, 9], [21, 11], [19, 11], [19, 9]]]}
        lat, lon = pipeline.centroid_of_rings(geom)
        self.assertAlmostEqual(lat, 9.8, places=1)
        self.assertAlmostEqual(lon, 19.8, places=1)

    def test_missing_geometry(self):
        self.assertEqual(pipeline.centroid_of_rings(None), (None, None))
        self.assertEqual(pipeline.centroid_of_rings({}), (None, None))


class TestParseDate(unittest.TestCase):
    def test_us_format(self):
        self.assertEqual(pipeline.parse_date("03/16/2026"), datetime(2026, 3, 16))

    def test_iso_format(self):
        self.assertEqual(pipeline.parse_date("2026-03-16"), datetime(2026, 3, 16))

    def test_invalid_returns_none(self):
        self.assertIsNone(pipeline.parse_date("not-a-date"))
        self.assertIsNone(pipeline.parse_date(""))
        self.assertIsNone(pipeline.parse_date(None))


class TestParseCityState(unittest.TestCase):
    def test_city_state_zip(self):
        self.assertEqual(pipeline.parse_city_state("LYNCHBURG, VA 24551"), ("LYNCHBURG", "VA"))

    def test_city_state_no_zip(self):
        self.assertEqual(pipeline.parse_city_state("FOREST VA"), ("FOREST", "VA"))

    def test_empty(self):
        self.assertEqual(pipeline.parse_city_state(""), ("", ""))
        self.assertEqual(pipeline.parse_city_state(None), ("", ""))

    def test_no_state(self):
        # No two-letter state code → entire string is "city", state is empty
        city, state = pipeline.parse_city_state("Some City")
        self.assertEqual(state, "")


class TestEstimateHh(unittest.TestCase):
    def test_sqft_buckets(self):
        # Small house
        size, basis = pipeline.estimate_hh(900, 0)
        self.assertAlmostEqual(size, 1.8)
        self.assertIn("sqft=", basis)

        # Mid house (≤2500 bracket)
        size, _ = pipeline.estimate_hh(2200, 0)
        self.assertAlmostEqual(size, 3.0)

        # Big house
        size, _ = pipeline.estimate_hh(3800, 0)
        self.assertAlmostEqual(size, 3.5)

    def test_price_fallback(self):
        size, basis = pipeline.estimate_hh(None, 350000)
        self.assertAlmostEqual(size, 2.7)
        self.assertIn("$350,000", basis)

    def test_zero_price_zero_sqft(self):
        size, basis = pipeline.estimate_hh(None, 0)
        self.assertAlmostEqual(size, 2.0)
        self.assertEqual(basis, "non-market")

    def test_br_takes_priority(self):
        # BR overrides sqft/price when present
        size, basis = pipeline.estimate_hh(900, 100000, br=5)
        self.assertAlmostEqual(size, 4.6)
        self.assertEqual(basis, "br=5")

    def test_br_caps_high(self):
        # BR > 6 caps at the 6-BR row
        size, basis = pipeline.estimate_hh(None, None, br=8)
        self.assertAlmostEqual(size, 5.3)
        self.assertEqual(basis, "br=8")

    def test_br_falsy_falls_through(self):
        # BR=0 or empty falls through to sqft/price
        size, basis = pipeline.estimate_hh(None, 200000, br=0)
        self.assertIn("price=", basis)


class TestIsLikelyRental(unittest.TestCase):
    def test_entity_owner_is_rental(self):
        self.assertTrue(pipeline.is_likely_rental(
            "ACME PROPERTIES LLC", "100 OFFICE PARK", "200 HOUSE LN", datetime.now()))

    def test_owner_occupied_matching_addr(self):
        self.assertFalse(pipeline.is_likely_rental(
            "SMITH JOHN", "200 HOUSE LN", "200 HOUSE LN", datetime.now()))

    def test_empty_mail_addr_is_owner_occupied(self):
        # No mail data = assume owner-occupied (don't drop)
        self.assertFalse(pipeline.is_likely_rental(
            "SMITH JOHN", "", "200 HOUSE LN", datetime.now()))

    def test_recent_sale_grace_period(self):
        # Mismatched but within 90 days → keep (mail not yet updated)
        recent = datetime.now() - timedelta(days=30)
        self.assertFalse(pipeline.is_likely_rental(
            "SMITH JOHN", "OLD ADDR", "NEW ADDR", recent))

    def test_old_sale_mismatch_is_rental(self):
        # Mismatched and beyond grace → landlord
        old = datetime.now() - timedelta(days=200)
        self.assertTrue(pipeline.is_likely_rental(
            "SMITH JOHN", "OWNER ADDR", "RENTAL ADDR", old))


class TestIsNonMarketTransfer(unittest.TestCase):
    """Filters out spouse retitles, gifts, trusts, and $0 transfers."""

    def test_spouse_retitle_with_zero_price(self):
        # Mariea case: husband removed from deed, $0 transfer
        self.assertTrue(pipeline.is_non_market_transfer(
            "REYNOLDS TERRY D & MARIEA H", "REYNOLDS MARIEA H", 0))

    def test_real_arms_length_sale(self):
        # Rivers case: different family bought from Taylor for $310K
        self.assertFalse(pipeline.is_non_market_transfer(
            "TAYLOR THOMAS A & ROBERTA",
            "RIVERS DAVID & RIVERS KATE & WOLF LU", 310000))

    def test_zero_price_no_overlap_still_dropped(self):
        # Gift / trust transfer between unrelated-named parties
        self.assertTrue(pipeline.is_non_market_transfer(
            "ABC HOLDINGS LLC", "SMITH JOHN", 0))

    def test_same_surname_unrelated_kept(self):
        # Two unrelated Smiths: surname overlap alone is not enough
        self.assertFalse(pipeline.is_non_market_transfer(
            "SMITH JOHN", "SMITH MARY", 200000))

    def test_spouse_retitle_with_nominal_price(self):
        # Same family on both sides, even with non-zero price
        self.assertTrue(pipeline.is_non_market_transfer(
            "JONES BOB & JANE", "JONES JANE", 1))

    def test_missing_grantor_falls_back_to_price(self):
        # Counties without grantor data: price=0 still drops, real price keeps
        self.assertTrue(pipeline.is_non_market_transfer("", "SMITH JOHN", 0))
        self.assertFalse(pipeline.is_non_market_transfer("", "SMITH JOHN", 200000))

    def test_stopwords_dont_create_false_overlap(self):
        # "TRUST" appearing in both shouldn't count as a name match
        self.assertFalse(pipeline.is_non_market_transfer(
            "DOE FAMILY TRUST", "SMITH LIVING TRUST", 250000))


class TestIsChineseFullname(unittest.TestCase):
    def test_clear_chinese_name(self):
        self.assertTrue(pipeline.is_chinese_fullname("ZHANG WEI"))
        self.assertTrue(pipeline.is_chinese_fullname("WANG, XIAOMING"))

    def test_chinese_surname_english_given(self):
        # CHANG is Chinese surname but WAYNE is English → not flagged
        self.assertFalse(pipeline.is_chinese_fullname("CHANG WAYNE"))

    def test_non_chinese_surname(self):
        self.assertFalse(pipeline.is_chinese_fullname("SMITH JOHN"))

    def test_couple_one_chinese(self):
        # "&" splits into parts; either side qualifying = True
        self.assertTrue(pipeline.is_chinese_fullname("SMITH JOHN & ZHANG WEI"))

    def test_non_string_input(self):
        self.assertFalse(pipeline.is_chinese_fullname(None))
        self.assertFalse(pipeline.is_chinese_fullname(123))


class TestDownloadCampbell(unittest.TestCase):
    """Regression test for the address-formatting bug fixed in 2ba52ad.

    Old behavior: '69.0 VIKING' (float decimal + missing street type)
    New behavior: '69 VIKING LN'
    """

    def _make_response(self, attributes_list):
        resp = MagicMock()
        resp.json.return_value = {
            "features": [
                {
                    "attributes": attrs,
                    "geometry": {"rings": [[[-79.25, 37.33], [-79.24, 37.33],
                                            [-79.24, 37.34], [-79.25, 37.34],
                                            [-79.25, 37.33]]]},
                }
                for attrs in attributes_list
            ]
        }
        return resp

    @patch("find_all_homeowners_20mi.requests.get")
    def test_address_includes_street_type_and_no_decimal(self, mock_get):
        mock_get.side_effect = [
            self._make_response([
                {"NAME1": "CHANG WAYNE & KIYANA P", "STRTNUM": 69.0,
                 "STRTNAME": "VIKING", "STRTTYPE": "LN", "STRTCITY": "FOREST",
                 "STRTZIP": "24551", "SALE1D": 1742083200000, "SALE1AMT": 403985.0},
                {"NAME1": "SEGNER COLE B", "STRTNUM": 90.0,
                 "STRTNAME": "CATALPA", "STRTTYPE": "RD", "STRTCITY": "LYNCHBURG",
                 "STRTZIP": "24502", "SALE1D": 1742083200000, "SALE1AMT": 250000.0},
            ]),
            self._make_response([]),  # second page empty → loop terminates
        ]

        df = pipeline.download_campbell("2025-01-01")

        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["LocAddr"], "69 VIKING LN")
        self.assertEqual(df.iloc[1]["LocAddr"], "90 CATALPA RD")
        # No record should have ".0" decimal in the address
        for addr in df["LocAddr"]:
            self.assertNotIn(".0", addr)

    @patch("find_all_homeowners_20mi.requests.get")
    def test_outfields_request_includes_strttype(self, mock_get):
        mock_get.return_value = self._make_response([])
        pipeline.download_campbell("2025-01-01")
        # First positional arg should be the URL; outFields lives in params kwarg
        _, kwargs = mock_get.call_args
        self.assertIn("STRTTYPE", kwargs["params"]["outFields"])

    @patch("find_all_homeowners_20mi.requests.get")
    def test_missing_street_number_does_not_inject_zero(self, mock_get):
        mock_get.side_effect = [
            self._make_response([
                {"NAME1": "VACANT LOT OWNER", "STRTNUM": None,
                 "STRTNAME": "HOMEWOOD", "STRTTYPE": "DR", "STRTCITY": "FOREST",
                 "STRTZIP": "24551", "SALE1D": 1742083200000, "SALE1AMT": 0},
            ]),
            self._make_response([]),
        ]

        df = pipeline.download_campbell("2025-01-01")

        self.assertEqual(df.iloc[0]["LocAddr"], "HOMEWOOD DR")

    @patch("find_all_homeowners_20mi.requests.get")
    def test_missing_street_type_still_works(self, mock_get):
        mock_get.side_effect = [
            self._make_response([
                {"NAME1": "X", "STRTNUM": 100.0, "STRTNAME": "MAIN",
                 "STRTTYPE": None, "STRTCITY": "FOREST", "STRTZIP": "24551",
                 "SALE1D": 1742083200000, "SALE1AMT": 100000.0},
            ]),
            self._make_response([]),
        ]

        df = pipeline.download_campbell("2025-01-01")

        # Missing STRTTYPE → no trailing space, no "None" string
        self.assertEqual(df.iloc[0]["LocAddr"], "100 MAIN")


class TestFrontendAddressRegex(unittest.TestCase):
    """The frontend strips '^\\d+\\.0\\s*' from LocAddr (app/src/lib/format.ts).

    These tests document that the new Python output no longer triggers that
    band-aid — i.e., addresses survive intact through to the UI.
    """

    import re
    _FMT_ADDR_RE = re.compile(r"^\d+\.0\s*")

    def _fmt_addr(self, s):
        cleaned = self._FMT_ADDR_RE.sub("", s).strip()
        return cleaned or "Address on file"

    def test_old_buggy_address_loses_house_number(self):
        # The old bug: '69.0 VIKING' → frontend strips '69.0 ' → just 'VIKING'
        self.assertEqual(self._fmt_addr("69.0 VIKING"), "VIKING")

    def test_new_address_survives(self):
        self.assertEqual(self._fmt_addr("69 VIKING LN"), "69 VIKING LN")
        self.assertEqual(self._fmt_addr("1102 WALKERS CROSSING DRIVE"),
                         "1102 WALKERS CROSSING DRIVE")

    def test_empty_falls_back_to_placeholder(self):
        self.assertEqual(self._fmt_addr(""), "Address on file")


if __name__ == "__main__":
    unittest.main()
