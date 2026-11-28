"""Platform storefronts (2026-11-27).

Under the Founder's storefront standard of 2026-11-26 (a platform's
storefront opens into its full service suite, selling access
globally), this test pins the storefront machinery: every platform
of record renders a storefront from its definition; the page carries
its six codes, its suite, the four companies, and the exact served
seal assets; a live Stripe product and price of record render where
they exist; and no price renders where none is settled or ruled —
Grantwriter's page in particular shows no price and no product.
"""

import html
import unittest

from core_platform.platform_definitions import DEFINITIONS
from core_platform.platform_storefront import (
    render_directory, render_storefront)


class PlatformStorefrontTest(unittest.TestCase):

    def test_every_platform_renders(self):
        for pid, defn in DEFINITIONS.items():
            status, body = render_storefront(pid)
            self.assertEqual(status, '200 OK', pid)
            page = body.decode('utf-8')
            self.assertIn(html.escape(defn.name), page, pid)
            self.assertIn('/assets/seal-corporate-hq.png', page, pid)
            self.assertIn('S &amp; G Security Inc.', page, pid)
            self.assertNotIn('<script', page, pid)
            if defn.naics_codes:
                for code in defn.naics_codes:
                    self.assertIn(code, page, pid)

    def test_unknown_platform_is_404(self):
        status, _ = render_storefront('no_such_platform')
        self.assertEqual(status, '404 Not Found')

    def test_live_product_and_price_render(self):
        status, body = render_storefront('sanders_finance')
        page = body.decode('utf-8')
        self.assertEqual(status, '200 OK')
        self.assertIn('prod_Vh6YjFk8GUDCRG', page)
        self.assertIn('$7,999,600', page)

    def test_grantwriter_shows_her_ruled_price(self):
        # Founder ruling 2026-11-27 (deliberation program): her two
        # lanes are OF RECORD and her storefront shows them.
        status, body = render_storefront('grantwriter')
        page = body.decode('utf-8')
        self.assertEqual(status, '200 OK')
        self.assertIn('price of record', page)
        self.assertIn('$49', page)
        self.assertIn('$99/mo', page)
        self.assertIn('$15,000', page)
        self.assertNotIn('prod_', page)
        self.assertNotIn('%', page)

    def test_ruled_price_shows_of_record(self):
        # The designed-figure conflict was ruled in the deliberation
        # program of 2026-11-27: the storefront now shows the price
        # of record, and the superseded designed figures stay absent.
        status, body = render_storefront('sanders_sentinel')
        page = body.decode('utf-8')
        self.assertEqual(status, '200 OK')
        self.assertIn('price of record', page)
        self.assertIn('$250,000/yr', page)
        self.assertNotIn('$455,000,000', page)
        self.assertNotIn('$7,999,600', page)

    def test_headquarters_ten_codes_render(self):
        # Founder ruling, 2026-11-27: Headquarters holds ten codes;
        # its storefront renders all ten and says so.
        status, body = render_storefront('s_and_g_security_inc')
        page = body.decode('utf-8')
        self.assertEqual(status, '200 OK')
        for code in ('551114', '561612', '561621', '541611', '541512',
                     '541618', '523999', '541219', '561110', '561410'):
            self.assertIn(code, page)
        self.assertIn('Its Ten Industries', page)
        self.assertNotIn("Founder's to rule",
                         page.replace('&#x27;', "'"))

    def test_juggernaut_ruled_none(self):
        status, body = render_storefront('juggernaut')
        page = body.decode('utf-8')
        self.assertEqual(status, '200 OK')
        self.assertIn('as ruled', page)

    def test_directory_lists_every_platform(self):
        page = render_directory().decode('utf-8')
        self.assertEqual(page.count('href="/platforms/'), len(DEFINITIONS))
        for pid in DEFINITIONS:
            self.assertIn('href="/platforms/%s"' % pid, page)


if __name__ == '__main__':
    unittest.main()
