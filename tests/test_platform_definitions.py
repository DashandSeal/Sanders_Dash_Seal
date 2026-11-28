"""Platform definitions (2026-11-27).

Under the Founder's orders of 2026-11-26 (finish the platforms;
every platform fully defined in its own record), this test pins
the definition pass: the 65 platforms that held no built identity
record now hold one in core_platform/platform_definitions.py,
carrying exactly their reconciled six from the NACI six-code
reconciliation of 2026-11-26; every platform of record holds a
complete definition; and the ruled sets stand untouched — the
anchored six, JUGGERNAUT's none, SEIC's eight, Grantwriter's
composed six and her two-lane public price ruled 2026-11-27. Headquarters' ten codes,
ruled by the Founder on 2026-11-27 (13:47 MST, "Agreed"), are
pinned by test_headquarters_ten_codes_ruled below.

Landing of 2026-11-27 (Oikos + Gaia Mind): Oikos joins the
record by the Founder’s direction — a further identity record
(the 67th, Headquarters having landed first) and a 162nd
definition, carrying her seven ruled codes (one per continent)
as a named exception beside SEIC’s eight; and the gia_mind
definition carries the corrected name Gaia Mind under the
Founder’s ruling of 2026-11-27 13:10 MST, her codes and her
unsettled price untouched.
"""

import unittest

from core_platform.platform_definitions import (
    DEFINITIONS, IDENTITIES, definition_for, identity_for)

EXPECTED_SIXES = {
    'ai_role_workers': ('541511', '541512', '541513', '518210', '541519', '541690'),
    'ai_strategy': ('541611', '541512', '541511', '541513', '541519', '541618'),
    'alph': ('541512', '541513', '541519', '561621', '518210', '541690'),
    'bata': ('561621', '541519', '541512', '518210', '561612', '541690'),
    'big_data_mind': ('541512', '518210', '541511', '541513', '541519', '541618'),
    'combat_academy': ('611699', '611620', '541618', '541512', '541511', '541513'),
    'daedalus': ('541715', '541511', '541512', '518210', '541519', '541690'),
    'elite_leadership': ('611430', '541611', '541618', '541512', '541511', '541513'),
    'family_council': ('624190', '624120', '541618', '541512', '541511', '541513'),
    'freedom_ops': ('541611', '541618', '541512', '541511', '541513', '541519'),
    'goliath': ('541511', '541512', '541519', '518210', '519190', '541715'),
    'guardian_sentinel': ('561621', '561612', '541618', '541512', '541611', '561499'),
    'guardian_watchdog': ('561621', '541519', '541512', '561612', '518210', '541690'),
    'hades': ('541512', '518210', '541511', '541519', '541690', '561499'),
    'health_solutions': ('621610', '621999', '621399', '541618', '541512', '541511'),
    'judge': ('541110', '541199', '541512', '518210', '541690', '922190'),
    'knowledge_base': ('519120', '518210', '541511', '541512', '541513', '541618'),
    'kronos': ('541512', '518210', '541511', '541513', '541519', '541690'),
    'michael_angelo': ('541511', '541512', '541611', '518210', '541690', '519190'),
    'mind_guardian': ('621330', '621999', '541618', '541512', '541511', '541513'),
    'money_factory_legal_aid': ('541110', '541199', '541512', '518210', '561499', '519190'),
    'platform1_33_ship_it_stub_collective': ('541511', '541512', '541513', '541519', '518210', '541690'),
    'police_men': ('561612', '561611', '541512', '541199', '561621', '541690'),
    's_and_g_security_inc': ('551114', '561612', '561621', '541611', '541512', '541618', '523999', '541219', '561110', '561410'),
    'sanders_advanced_academics': ('611110', '611310', '611430', '541618', '541512', '541511'),
    'sanders_ai_lab': ('541715', '541714', '541713', '541519', '541618', '541690'),
    'sanders_ai_recognition': ('541512', '541511', '541513', '541519', '541618', '541690'),
    'sanders_archive': ('519120', '519130', '541519', '541618', '541690', '541512'),
    'sanders_big_brother_govops': ('541820', '541611', '541618', '541690', '561110', '561621'),
    'sanders_biology': ('541714', '541715', '621511', '621999', '541618', '541690'),
    'sanders_chemistry': ('325998', '325199', '541715', '541618', '541690', '541714'),
    'sanders_compliance': ('541611', '541612', '541618', '541690', '541990', '541512'),
    'sanders_construction': ('236220', '236210', '541618', '541512', '541690', '541611'),
    'sanders_cybersec': ('541519', '541511', '541512', '541618', '541690', '611420'),
    'sanders_dash_and_seal': ('541199', '541110', '541512', '541511', '518210', '519190'),
    'sanders_emergency_global_communication': ('517919', '624230', '541512', '518210', '541690', '922190'),
    'sanders_environment': ('541620', '541690', '541618', '541512', '541513', '541715'),
    'sanders_fitness_and_wellness': ('713940', '621399', '541618', '541512', '541511', '541513'),
    'sanders_gatekeeper_audit': ('541211', '541219', '541213', '541214', '541618', '541690'),
    'sanders_health': ('621111', '621112', '621999', '622110', '623110', '541715'),
    'sanders_healthtech': ('541715', '541513', '541519', '621111', '621511', '622110'),
    'sanders_integration': ('541512', '541513', '541519', '541611', '541618', '541690'),
    'sanders_leadership_institute': ('611430', '611699', '541618', '541512', '541511', '541513'),
    'sanders_martial_academy': ('611699', '611620', '541618', '541512', '541511', '541513'),
    'sanders_nexus_shield': ('561621', '541512', '518210', '541519', '561612', '541690'),
    'sanders_ops': ('541614', '541618', '561110', '561621', '541512', '541690'),
    'sanders_quantum_computing': ('541511', '541512', '541519', '541715', '541690', '518210'),
    'sanders_secure_stack': ('541512', '518210', '561621', '541519', '541513', '541690'),
    'sanders_signal': ('519130', '541810', '541613', '518210', '541511', '519190'),
    'sanders_six_industry': ('621610', '624120', '485991', '532283', '423450', '492110'),
    'sanders_six_shield': ('561621', '541512', '541519', '561612', '541618', '518210'),
    'sanders_space': ('336414', '336411', '336413', '541715', '541618', '541690'),
    'sanders_strategy': ('541611', '541612', '541618', '541690', '541512', '541513'),
    'sanders_tactical_training': ('611699', '541618', '541512', '541511', '541513', '541519'),
    'sanders_teacher_physics': ('541715', '541714', '541713', '541618', '541690', '541512'),
    'sanders_travel': ('561510', '561520', '561599', '488510', '541618', '541690'),
    'secretary': ('561110', '541110', '541199', '541611', '518210', '519190'),
    'stream_api': ('518210', '541512', '522320', '541511', '541519', '561499'),
    'tactical_edge': ('541611', '541618', '541512', '541511', '541513', '541519'),
    'twostep': ('541512', '518210', '541519', '561621', '541690', '519190'),
    'upgrade_sidecar': ('541511', '541512', '541513', '518210', '541519', '541690'),
    'voice_audio_video': ('517919', '518210', '541511', '541512', '512191', '519130'),
    'watchdog_beta': ('541512', '541618', '541511', '541513', '541519', '541690'),
    'wellness_center': ('621399', '713940', '541618', '541512', '541511', '541513'),
    'white_phoenix': ('541512', '541511', '518210', '541715', '541519', '541690'),
    'zone_watch': ('541512', '518210', '541519', '561621', '541110', '519190'),
}

ANCHORED = ('621610', '624120', '485991', '532283', '423450', '492110')


class PlatformDefinitionsTest(unittest.TestCase):

    def test_sixty_seven_new_identity_records(self):
        # The 65 of the reconciliation, plus Headquarters (ten
        # codes ruled 2026-11-27) and Oikos — the 67th identity
        # record, added by Founder direction 2026-11-27.
        self.assertEqual(len(IDENTITIES), 67)
        for pid, identity in IDENTITIES.items():
            self.assertEqual(identity.status, 'DEFINED')
            self.assertEqual(identity.platform_id, pid)

    def test_identity_sixes_match_the_reconciliation(self):
        self.assertEqual(set(EXPECTED_SIXES) | {'oikos'},
                         set(IDENTITIES))
        for pid, six in EXPECTED_SIXES.items():
            self.assertEqual(tuple(IDENTITIES[pid].naics_codes), six, pid)

    def test_every_platform_of_record_is_defined(self):
        self.assertEqual(len(DEFINITIONS), 162)
        for pid, defn in DEFINITIONS.items():
            self.assertTrue(defn.who.strip(), pid)
            self.assertTrue(defn.why.strip(), pid)
            self.assertTrue(defn.serves.strip(), pid)
            self.assertTrue(defn.business_model.strip(), pid)
            self.assertTrue(defn.service_suite, pid)
            self.assertEqual(len(defn.companies), 4, pid)

    def test_codes_shape_and_ruled_sets(self):
        for pid, defn in DEFINITIONS.items():
            if pid in ('juggernaut', 'carehive_os'):
                self.assertEqual(defn.naics_codes, (), pid)
            elif pid == 'sanders_ethics_impact_collective':
                self.assertEqual(len(defn.naics_codes), 8, pid)
            elif pid == 'oikos':
                self.assertEqual(len(defn.naics_codes), 7, pid)
            elif pid == 's_and_g_security_inc':
                self.assertEqual(len(defn.naics_codes), 10, pid)
            else:
                self.assertEqual(len(defn.naics_codes), 6, pid)
        self.assertEqual(
            DEFINITIONS['uncle_nickey_mao'].naics_codes, ANCHORED)
        self.assertEqual(
            DEFINITIONS['sanders_home_healthcare'].naics_codes, ANCHORED)

    def test_headquarters_ten_codes_ruled(self):
        # Founder ruling, 2026-11-27 13:47 MST ("Agreed"):
        # Headquarters holds TEN NACI codes, not six — its span is
        # the whole house. They stand identically in Headquarters'
        # identity record and its definition.
        ten = ('551114', '561612', '561621', '541611', '541512',
               '541618', '523999', '541219', '561110', '561410')
        self.assertEqual(
            tuple(IDENTITIES['s_and_g_security_inc'].naics_codes), ten)
        self.assertEqual(
            DEFINITIONS['s_and_g_security_inc'].naics_codes, ten)
        self.assertEqual(
            IDENTITIES['s_and_g_security_inc'].status, 'DEFINED')

    def test_grantwriter_price_ruled(self):
        # Founder ruling, 2026-11-27 (10:02 MST, two lanes; Lane B as
        # repriced by the value-repricing pass ruled 12:00 MST): her
        # public price is OF RECORD. Percentage-of-award pricing is
        # barred (GPA Ethics / AFP / 2 CFR 200.442) and never encoded.
        defn = DEFINITIONS['grantwriter']
        self.assertEqual(
            defn.naics_codes,
            ('541611', '541612', '541618', '541512', '611430', '813211'))
        self.assertTrue(defn.price_of_record.startswith('OF RECORD'))
        for figure in ('$49', '$99/mo', '$15,000', '$4,950/mo'):
            self.assertIn(figure, defn.price_of_record)
        self.assertNotIn('%', defn.price_of_record)
        self.assertNotIn('prod_', defn.stripe_product)

    def test_daedalus_repair_core_product(self):
        # Founder ruling, 2026-11-26/27: Daedalus's product of record
        # is that he is the one that gets plugged into everything to
        # repair it — the ecosystem's repair core, global by design;
        # ensuring he performs well is a standing priority.
        defn = DEFINITIONS['daedalus']
        for field in (defn.who, defn.why, defn.business_model):
            self.assertIn('repair core', field)
            self.assertIn('plugged into everything', field)
        self.assertIn('standing priority', defn.why)
        # His price was ruled 2026-11-27: enterprise agreements
        # only — no shelf price; the floor and the standard
        # sovereign engagement stand in the record (standard as
        # repriced by the value-repricing pass, 12:00 MST).
        self.assertTrue(
            defn.price_of_record.startswith('ENTERPRISE AGREEMENTS'))
        self.assertIn('$250,000/yr', defn.price_of_record)
        self.assertIn('$495,000/yr', defn.price_of_record)

    def test_oikos_identity_and_definition(self):
        # Founder direction and rulings, 2026-11-27: Oikos is a
        # new platform beyond the 140 — humanity's Home, seven
        # codes, one per continent; institutions fund the
        # necessities and her served populations are never her
        # payers.
        seven = ('621610', '111998', '541715', '221118',
                 '236220', '221310', '541690')
        identity = identity_for('oikos')
        self.assertIsNotNone(identity)
        self.assertEqual(identity.status, 'DEFINED')
        self.assertEqual(tuple(identity.naics_codes), seven)
        defn = DEFINITIONS['oikos']
        self.assertEqual(defn.name, 'Oikos')
        self.assertEqual(tuple(defn.naics_codes), seven)
        self.assertEqual(len(defn.service_suite), 7)
        self.assertIn('$250,000', defn.price_of_record)
        self.assertIn('$1,000,000', defn.price_of_record)
        self.assertIn('never her payers', defn.business_model)
        self.assertIn('never her payers', defn.serves)
        self.assertIn('learns and grows', defn.business_model)

    def test_gaia_mind_name_corrected(self):
        # Founder ruling 2026-11-27 13:10 MST: "It's Gaia mind."
        # The name is corrected and her codes stand untouched; her
        # price was ruled separately the same day in the
        # deliberation program (OF RECORD — see
        # test_prices_of_record_ruled_2026_11_27).
        defn = DEFINITIONS['gia_mind']
        self.assertEqual(defn.name, 'Gaia Mind')
        self.assertIn('2026-11-27', defn.provenance)
        self.assertEqual(
            defn.naics_codes,
            ('621330', '621112', '621999', '541618', '541512', '541690'))
        self.assertTrue(defn.price_of_record.startswith('OF RECORD'))
        from core_platform.gia_mind_service import IDENTITY
        self.assertEqual(IDENTITY.name, 'Gaia Mind')
        self.assertEqual(tuple(IDENTITY.naics_codes), defn.naics_codes)

    def test_prices_of_record_ruled_2026_11_27(self):
        # The deliberation program of 2026-11-27 ruled every one of
        # the 21 designed-figure conflicts (with the value-repricing
        # pass); each price of record now stands in its definition.
        ruled = (
            'sanders_legal_helpers', 'sanders_recon', 'sanders_coordinator',
            'sanders_education', 'sanders_logistics', 'sanders_security',
            'sanders_energy', 'sanders_communications', 'showtime',
            'sanders_patriot_saint', 'sanders_steward_sentinel', 'ai_doctor',
            'sanders_ai_psychiatrist', 'lil_mama', 'baby_girl',
            'sanders_sentinel', 'sanders_research', 'sanders_ai_research',
            'gia_mind', 'sanders_freedom_revolution', 'grantwriter')
        for pid in ruled:
            defn = DEFINITIONS[pid]
            self.assertTrue(
                defn.price_of_record.startswith('OF RECORD'), pid)
            self.assertIn('$', defn.price_of_record, pid)
            self.assertNotIn('prod_', defn.stripe_product, pid)
        for pid, defn in DEFINITIONS.items():
            self.assertFalse(
                defn.price_of_record.startswith('NOT SETTLED'), pid)
            self.assertFalse(
                defn.price_of_record.startswith('UNRULED'), pid)

    def test_accessors(self):
        self.assertIs(definition_for('grantwriter'),
                      DEFINITIONS['grantwriter'])
        self.assertIsNone(definition_for('no_such_platform'))
        self.assertIsNone(identity_for('grantwriter'))
        for pid in IDENTITIES:
            self.assertIs(identity_for(pid), IDENTITIES[pid])
            self.assertEqual(
                tuple(DEFINITIONS[pid].naics_codes),
                tuple(IDENTITIES[pid].naics_codes), pid)


if __name__ == '__main__':
    unittest.main()
