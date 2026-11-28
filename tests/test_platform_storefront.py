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

    def _card(self, page, pid):
        start = page.index('<article class="card"><h3>'
                           '<a href="/platforms/%s">' % pid)
        return page[start:page.index('</article>', start)]

    def test_directory_shows_ruled_price_on_the_card(self):
        # The shelf (Founder priority, 2026-11-28): a platform's
        # price of record stands on its directory card itself, in
        # the same string its Access panel prints — not one click
        # deep. Grantwriter is a deliberation-ruled platform.
        page = render_directory().decode('utf-8')
        defn = DEFINITIONS['grantwriter']
        self.assertIn(html.escape(defn.price_of_record),
                      self._card(page, 'grantwriter'))
        self.assertIn('$49', self._card(page, 'grantwriter'))
        self.assertIn('$99/mo', self._card(page, 'grantwriter'))

    def test_directory_shows_live_product_price_on_the_card(self):
        # A Stripe-backed platform's card carries the same price
        # string its Access panel shows today — displayed as it
        # already appears, with no new label on it.
        page = render_directory().decode('utf-8')
        defn = DEFINITIONS['sanders_finance']
        self.assertIn(html.escape(defn.price_of_record),
                      self._card(page, 'sanders_finance'))
        self.assertIn('$7,999,600', self._card(page, 'sanders_finance'))

    def test_directory_daedalus_card_shows_no_shelf_price(self):
        # Daedalus stands under enterprise agreements only (ruled
        # 2026-11-27): her card states that and shows no price.
        page = render_directory().decode('utf-8')
        card = self._card(page, 'daedalus')
        self.assertIn('Enterprise agreements only', card)
        self.assertIn('no shelf price', card)
        self.assertNotIn('$', card)

    def test_directory_unpriced_platform_shows_no_price_line(self):
        # No price is invented for the shelf: a platform with no
        # price of record carries no price line on its card.
        page = render_directory().decode('utf-8')
        unpriced = [pid for pid, d in DEFINITIONS.items()
                    if not (d.stripe_product or '').startswith('YES')
                    and not (d.price_of_record or '').startswith(
                        ('OF RECORD', 'ENTERPRISE AGREEMENTS'))]
        self.assertTrue(unpriced)
        for pid in unpriced:
            self.assertNotIn('price-line', self._card(page, pid), pid)

    def test_directory_price_line_count_matches_the_record(self):
        # One price line per priced platform of record, plus
        # Daedalus's no-shelf-price line — and no others.
        page = render_directory().decode('utf-8')
        priced = sum(
            1 for d in DEFINITIONS.values()
            if (d.stripe_product or '').startswith('YES')
            or (d.price_of_record or '').startswith(
                ('OF RECORD', 'ENTERPRISE AGREEMENTS')))
        self.assertEqual(page.count('class="price-line"'), priced)


if __name__ == '__main__':
    unittest.main()
