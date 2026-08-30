from __future__ import annotations

import json
import io
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_kb import (  # noqa: E402
    build_database,
    detect_conflicts,
    normalize_checkpoint_advice,
    validate_checkpoint_advice_evidence,
)
from achievement_report import load_achievement_report  # noqa: E402
from checkpoint_report import load_report  # noqa: E402
from conflict_report import load_conflicts  # noqa: E402
from early_walkthrough import (  # noqa: E402
    classify_medal_tracking,
    load_walkthrough,
    print_walkthrough,
    resolve_checkpoint_range,
    main as early_walkthrough_main,
)
from medal_report import medals_available_through  # noqa: E402
from acquisition_availability import route_availability  # noqa: E402
from item_report import load_item_routes, load_purchase_advice  # noqa: E402
from monster_report import (  # noqa: E402
    load_checkpoint_monsters,
    load_monster_coverage,
    load_monster_report,
    print_monster_report,
)
from hoarder_report import load_hoarder_report  # noqa: E402
from player_progress import _load_state, update_progress  # noqa: E402
from query_kb import search  # noqa: E402
from vocation_report import load_vocation_details, print_vocation_details  # noqa: E402
from update_state import update_state  # noqa: E402
from walkthrough import main as walkthrough_main  # noqa: E402


class KnowledgeBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tempdir.name) / "test.sqlite"
        cls.counts = build_database(cls.db_path)
        cls.connection = sqlite3.connect(cls.db_path)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.tempdir.cleanup()

    def test_expected_seed_counts(self):
        self.assertEqual(self.counts["sources"], 720)
        self.assertEqual(self.counts["equipment_rules"], 6)
        self.assertEqual(self.counts["equipment_compatibility_audits"], 311)
        self.assertEqual(self.counts["equipment_compatibility"], 1866)
        self.assertEqual(self.counts["item_identity_redirects"], 1)
        self.assertEqual(self.counts["vocations"], 26)
        self.assertEqual(self.counts["medal_rewards"], 19)
        self.assertEqual(self.counts["missables"], 7)
        self.assertEqual(self.counts["mini_medal_locations"], 100)
        self.assertEqual(self.counts["checkpoint_obligations"], 223)
        self.assertEqual(self.counts["checkpoint_advice"], 116)
        self.assertEqual(self.counts["boss_skill_recommendations"], 8)
        self.assertEqual(self.counts["boss_skill_recommendation_evidence"], 15)
        self.assertEqual(self.counts["mini_medal_evidence"], 100)
        self.assertEqual(self.counts["item_categories"], 6)
        self.assertEqual(self.counts["items"], 355)
        self.assertEqual(self.counts["item_aliases"], 5)
        self.assertEqual(self.counts["item_acquisition_paths"], 748)
        self.assertEqual(self.counts["monster_hearts"], 46)

    def test_cp017_gladiator_burst_is_conditional_and_two_source_attributed(self):
        advice = self.connection.execute(
            """SELECT applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id = 'advice_cp017_gladiator_burst'"""
        ).fetchone()
        self.assertIsNotNone(advice)
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(applicability["requires"]["mastered"],
                         ["Warrior", "Martial Artist"])
        self.assertIn("does not prove unlock", applicability["availability_note"])
        self.assertIn("defence", applicability["tradeoff"].lower())
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(
            advice["verification_status"],
            "two_independent_current_version_editorial_sources_mechanic_and_role_match",
        )

        claims = self.connection.execute(
            """SELECT source_id, value_json, claim_kind, verification_status
            FROM claims
            WHERE subject_key = 'vocation:gladiator'
              AND predicate = 'recommended_power_role'
            ORDER BY source_id"""
        ).fetchall()
        self.assertEqual(
            {claim["source_id"] for claim in claims},
            {"game8_vocation_gladiator", "powerupgaming_vocation_tier_list"},
        )
        self.assertEqual(len({claim["value_json"] for claim in claims}), 1)
        self.assertTrue(all(claim["claim_kind"] == "recommendation"
                            for claim in claims))
        self.assertTrue(all(
            claim["verification_status"] ==
            "two_independent_current_version_editorial_sources"
            for claim in claims
        ))

    def test_cp027_champion_divide_is_conditional_and_two_source_attributed(self):
        advice = self.connection.execute(
            """SELECT subject, applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id = 'advice_cp027_champion_burst'"""
        ).fetchone()
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(advice["subject"], "Champion: Divide burst")
        self.assertEqual(applicability["requires"]["mastered"],
                         ["Gladiator", "Paladin"])
        self.assertIn("does not unlock", applicability["availability_note"])
        self.assertIn("optional power", applicability["safe_advancement"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(advice["verification_status"],
                         "two_independent_current_version_editorial_sources")

        claims = self.connection.execute(
            """SELECT source_id, value_json, claim_kind, verification_status
            FROM claims WHERE subject_key='vocation:champion'
            AND predicate='recommended_power_role' ORDER BY source_id"""
        ).fetchall()
        self.assertEqual({row["source_id"] for row in claims},
                         {"game8_vocation_champion", "gamewith_vocation_route"})
        self.assertEqual(len({row["value_json"] for row in claims}), 1)
        self.assertTrue(all(row["claim_kind"] == "recommendation"
                            for row in claims))
        self.assertTrue(all(
            row["verification_status"] ==
            "two_independent_current_version_editorial_sources"
            for row in claims
        ))

    def test_cp033_standard_arena_plan_is_scoped_gated_and_two_source(self):
        advice = self.connection.execute(
            """SELECT subject, applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id='advice_cp033_champion_arena_burst'"""
        ).fetchone()
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(advice["subject"], "Solo cups: Hero Divide burst")
        self.assertEqual(applicability["requires"], {
            "checkpoint_at_least": "cp_020_buccanham",
            "mastered": ["Gladiator", "Paladin"],
        })
        self.assertEqual(applicability["party_member"], "Hero")
        self.assertEqual(applicability["secondary_vocation"], "Martial Artist")
        self.assertIn("only", applicability["arena_scope"])
        self.assertEqual(set(applicability["excluded_scopes"]),
                         {"Rampage Roads", "DLC Road of Regal Wretches"})
        self.assertIn("first-clear", applicability["safe_advancement"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(
            advice["verification_status"],
            "two_independent_current_version_editorial_sources_standard_solo_cups",
        )

        claims = self.connection.execute(
            """SELECT source_id, value_json, claim_kind, scope_json,
            verification_status FROM claims
            WHERE subject_key='arena:standard_cups'
            AND predicate='recommended_power_plan' ORDER BY source_id"""
        ).fetchall()
        self.assertEqual({row["source_id"] for row in claims},
                         {"game8_battle_arena", "gamewith_battle_arena"})
        self.assertEqual(len({row["value_json"] for row in claims}), 1)
        self.assertTrue(all(row["claim_kind"] == "recommendation"
                            for row in claims))
        self.assertTrue(all(
            json.loads(row["scope_json"])["dlc"] ==
            "not_applicable_standard_cups" for row in claims
        ))

    def test_cp026_nottagen_boss_core_is_corroborated_and_extras_stay_single(self):
        advice = {row["advice_id"]: row for row in self.connection.execute(
            """SELECT advice_id, advice_text, applicability_json, confidence,
            verification_status FROM checkpoint_advice
            WHERE checkpoint_id='cp_026_elemental_cleanup_nottagen'
            AND advice_id IN ('advice_cp026_moostapha',
                              'advice_cp026_malign_vine')"""
        ).fetchall()}
        self.assertEqual(set(advice), {"advice_cp026_moostapha",
                                       "advice_cp026_malign_vine"})
        moostapha = json.loads(advice["advice_cp026_moostapha"]["applicability_json"])
        self.assertIn("Kabuff", moostapha["verified_core"]["defence"])
        self.assertEqual(moostapha["single_source_extras"]["source_id"],
                         "game8_boss_moostapha")
        self.assertIn("No exact level", moostapha["unknowns"])
        vine = json.loads(advice["advice_cp026_malign_vine"]["applicability_json"])
        self.assertFalse(vine["verified_core"]["target"].startswith("Defeat roots"))
        self.assertEqual(vine["single_source_extras"]["source_id"],
                         "game8_boss_malign_vine")
        self.assertIn("root-respawn", vine["unknowns"])
        self.assertTrue(all(row["confidence"] == "verified" for row in advice.values()))

        for subject, predicate, sources in (
            ("boss:moostapha", "recommended_physical_defence",
             {"game8_boss_moostapha", "neoseeker_nottagen_past"}),
            ("boss:malign_vine", "recommended_target_priority",
             {"game8_boss_malign_vine", "steam_achievement_walkthrough"}),
        ):
            claims = self.connection.execute(
                """SELECT source_id, value_json, claim_kind, verification_status
                FROM claims WHERE subject_key=? AND predicate=?""",
                (subject, predicate),
            ).fetchall()
            self.assertEqual({row["source_id"] for row in claims}, sources)
            self.assertEqual(len({row["value_json"] for row in claims}), 1)
            self.assertTrue(all(row["claim_kind"] == "recommendation"
                                for row in claims))
            self.assertTrue(all(row["verification_status"] ==
                                "two_independent_current_version_guides"
                                for row in claims))

    def test_cp016_power_route_is_two_source_and_keeps_the_grind_optional(self):
        advice = self.connection.execute(
            """SELECT subject, applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id = 'advice_cp016_advanced_path_routing'"""
        ).fetchone()
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(advice["subject"], "Power route: Champion + Druid")
        self.assertEqual(applicability["requires"]["checkpoint_at_least"],
                         "cp_012_roamer_return")
        self.assertEqual(applicability["party_assignments"],
                         {"Hero": "Champion", "Maribel": "Druid"})
        self.assertIn("optional", applicability["safe_advancement"])
        self.assertIn("no time/rate ceiling", applicability["optional_grind_ceiling"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(advice["verification_status"],
                         "two_independent_current_version_editorial_sources")

        for subject, predicate, sources in (
            ("character:hero", "recommended_endgame_vocations",
             {"game8_vocations_character", "gamewith_best_party"}),
            ("character:maribel", "recommended_endgame_vocation",
             {"game8_vocations_character", "gamewith_best_party"}),
        ):
            claims = self.connection.execute(
                """SELECT source_id, value_json, claim_kind, verification_status
                FROM claims WHERE subject_key=? AND predicate=?""",
                (subject, predicate),
            ).fetchall()
            self.assertEqual({row["source_id"] for row in claims}, sources)
            self.assertEqual(len({row["value_json"] for row in claims}), 1)
            self.assertTrue(all(row["claim_kind"] == "recommendation"
                                for row in claims))
            self.assertTrue(all(
                row["verification_status"] ==
                "two_independent_current_version_editorial_sources"
                for row in claims
            ))

    def test_cp019_cumulus_vex_separates_verified_core_from_single_source_extras(self):
        advice = self.connection.execute(
            """SELECT applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id = 'advice_cp019_cumulus_vex'"""
        ).fetchone()
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(
            advice["verification_status"],
            "two_source_verified_core_single_source_defence_and_healing",
        )
        self.assertIn("multi-target", applicability["verified_core"]["damage"])
        self.assertEqual(
            applicability["single_source_extras"]["source_id"],
            "game8_boss_cumulus_vex",
        )

        core = self.connection.execute(
            """SELECT source_id, value_json, verification_status
            FROM claims
            WHERE subject_key = 'boss:cumulus_vex'
              AND predicate = 'recommended_tactic'
            ORDER BY source_id"""
        ).fetchall()
        self.assertEqual(
            {row["source_id"] for row in core},
            {"game8_boss_cumulus_vex", "intoindiegames_aeolus"},
        )
        self.assertEqual(len({row["value_json"] for row in core}), 1)
        self.assertTrue(all(
            row["verification_status"] ==
            "two_independent_current_version_walkthroughs"
            for row in core
        ))

        extras = self.connection.execute(
            """SELECT source_id, verification_status
            FROM claims
            WHERE subject_key = 'boss:cumulus_vex'
              AND predicate = 'recommended_defence'"""
        ).fetchall()
        self.assertEqual(len(extras), 2)
        self.assertTrue(all(row["source_id"] == "game8_boss_cumulus_vex"
                            and row["verification_status"] == "single_source"
                            for row in extras))

    def test_cp028_orgodemir_separates_verified_core_from_single_publisher_extra(self):
        advice = self.connection.execute(
            """SELECT applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id = 'advice_cp028_orgodemir_final'"""
        ).fetchone()
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(
            advice["verification_status"],
            "two_source_verified_magic_barrier_and_phase_four_group_damage_single_source_benediction",
        )
        self.assertIn("Magic Barrier", applicability["verified_core"]["defence"])
        self.assertIn("multi-target", applicability["verified_core"]["phase_four"])
        self.assertEqual(applicability["single_source_extras"]["source_id"],
                         "game8_boss_orgodemir")
        self.assertIn("No exact level", applicability["unknowns"])

        for predicate in ("recommended_spell_defence",
                          "recommended_phase_four_add_response"):
            rows = self.connection.execute(
                """SELECT source_id, value_json, verification_status
                FROM claims
                WHERE subject_key = 'boss:orgodemir_final'
                  AND predicate = ?""", (predicate,)
            ).fetchall()
            self.assertEqual(
                {row["source_id"] for row in rows},
                {"game8_cathedral_blight_walkthrough",
                 "korosenai_orgodemir_final"},
            )
            self.assertEqual(len({row["value_json"] for row in rows}), 1)
            self.assertTrue(all(
                row["verification_status"] ==
                "two_independent_current_version_guides"
                for row in rows
            ))

        benediction = self.connection.execute(
            """SELECT source_id, verification_status FROM claims
            WHERE claim_id = 'claim_orgodemir_final_benediction_game8'"""
        ).fetchone()
        self.assertEqual(benediction["source_id"], "game8_boss_orgodemir")
        self.assertEqual(benediction["verification_status"],
                         "single_independent_publisher")

    def test_cp032_spirit_encounters_keep_verified_core_and_order_conflict_distinct(self):
        advice_rows = self.connection.execute(
            """SELECT advice_id, applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id IN ('advice_cp032_four_spirits',
                                'advice_cp032_almighty_spirits')"""
        ).fetchall()
        advice = {row["advice_id"]: row for row in advice_rows}
        standalone = json.loads(advice["advice_cp032_four_spirits"]
                                ["applicability_json"])
        combined = json.loads(advice["advice_cp032_almighty_spirits"]
                              ["applicability_json"])
        self.assertEqual(standalone["encounter"], "standalone Four Spirits")
        self.assertEqual(standalone["verified_core"]["target_priority"],
                         "Water Spirit first")
        self.assertEqual(standalone["single_source_extras"]["preparation"],
                         "Stock Dieamends")
        self.assertEqual(combined["encounter"],
                         "The Almighty plus Four Spirits")
        self.assertEqual(combined["unresolved_target_order"]["game8"],
                         ["Wind Spirit", "Fire Spirit"])
        self.assertEqual(combined["unresolved_target_order"]["neoseeker"],
                         ["Water Spirit", "Wind Spirit"])
        self.assertTrue(all(row["confidence"] == "verified"
                            for row in advice_rows))

        for subject, predicates in {
            "boss:four_spirits_standalone": (
                "recommended_target_priority", "recommended_spell_defence"),
            "boss:almighty_and_four_spirits": (
                "recommended_tether_response",),
        }.items():
            for predicate in predicates:
                rows = self.connection.execute(
                    """SELECT source_id, value_json, verification_status
                    FROM claims WHERE subject_key = ? AND predicate = ?""",
                    (subject, predicate),
                ).fetchall()
                self.assertEqual(
                    {row["source_id"] for row in rows},
                    {"game8_boss_four_spirits", "neoseeker_yet_another_world"}
                    if subject == "boss:four_spirits_standalone"
                    else {"game8_boss_almighty_spirits",
                          "neoseeker_yet_another_world"},
                )
                self.assertEqual(len({row["value_json"] for row in rows}), 1)
                self.assertTrue(all(
                    row["verification_status"] ==
                    "two_independent_current_version_guides"
                    for row in rows
                ))

        orders = self.connection.execute(
            """SELECT source_id, value_json, verification_status
            FROM claims
            WHERE subject_key = 'boss:almighty_and_four_spirits'
              AND predicate = 'recommended_pre_tether_target_order'"""
        ).fetchall()
        self.assertEqual(len({row["value_json"] for row in orders}), 2)
        self.assertTrue(all(row["verification_status"].startswith("single_source_conflicts")
                            for row in orders))

        # Recommendation conflicts are retained as attributed claims; automatic
        # canonical-fact conflict detection intentionally excludes them.
        self.assertEqual(
            {row["source_id"] for row in orders},
            {"game8_boss_almighty_spirits", "neoseeker_yet_another_world"},
        )

    def test_envoy_and_vaipur_verified_core_keeps_source_specific_extras(self):
        advice_rows = self.connection.execute(
            """SELECT advice_id, applicability_json, confidence
            FROM checkpoint_advice
            WHERE advice_id IN ('advice_cp016_envoy', 'advice_cp019_vaipur')"""
        ).fetchall()
        advice = {row["advice_id"]: row for row in advice_rows}
        envoy = json.loads(advice["advice_cp016_envoy"]["applicability_json"])
        vaipur = json.loads(advice["advice_cp019_vaipur"]["applicability_json"])
        self.assertIn("physical", envoy["verified_core"]["offence"].lower())
        self.assertEqual(set(envoy["source_mechanism_notes"]),
                         {"game8", "korosenai"})
        self.assertEqual(set(envoy["single_source_extras"]),
                         {"game8", "korosenai"})
        self.assertIn("spell resistance", vaipur["verified_core"]["defence"])
        self.assertIn("buffer", vaipur["verified_core"]["support"])
        self.assertEqual(set(vaipur["single_source_extras"]),
                         {"game8", "korosenai"})
        self.assertTrue(all(row["confidence"] == "verified"
                            for row in advice_rows))

        expected = {
            ("boss:the_envoy", "recommended_antimagic_response"):
                {"game8_boss_envoy", "korosenai_envoy"},
            ("boss:vaipur", "recommended_spell_defence"):
                {"game8_boss_vaipur", "korosenai_vaipur"},
            ("boss:vaipur", "recommended_support_role"):
                {"game8_boss_vaipur", "korosenai_vaipur"},
        }
        for (subject, predicate), sources in expected.items():
            rows = self.connection.execute(
                """SELECT source_id, value_json, confidence
                FROM claims WHERE subject_key=? AND predicate=?""",
                (subject, predicate),
            ).fetchall()
            self.assertEqual({row["source_id"] for row in rows}, sources)
            self.assertEqual(len({row["value_json"] for row in rows}), 1)
            self.assertTrue(all(row["confidence"] == "verified" for row in rows))

        envoy_extras = self.connection.execute(
            """SELECT value_json, verification_status FROM claims
            WHERE subject_key='boss:the_envoy'
              AND predicate='recommended_support_extra'"""
        ).fetchall()
        self.assertEqual(len(envoy_extras), 2)
        self.assertEqual(len({row["value_json"] for row in envoy_extras}), 2)
        self.assertTrue(all(row["verification_status"] ==
                            "single_independent_source"
                            for row in envoy_extras))

    def test_gasputin_verified_silence_response_preserves_lockout_dispute(self):
        advice = self.connection.execute(
            """SELECT applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id='advice_cp018_gasputin'"""
        ).fetchone()
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertIn("two_source_verified_physical_silence_response",
                      advice["verification_status"])
        self.assertEqual(applicability["verified_core"]["response"],
                         "Use physical attacks during Silence")
        self.assertEqual(set(applicability["source_mechanism_note"]),
                         {"game8", "intoindiegames_and_korosenai"})
        self.assertIn("source-disputed", applicability["unknowns"])

        core = self.connection.execute(
            """SELECT source_id, value_json, confidence, verification_status
            FROM claims WHERE subject_key='boss:gasputin'
              AND predicate='recommended_silence_response'"""
        ).fetchall()
        self.assertEqual(
            {row["source_id"] for row in core},
            {"intoindiegames_vogograd", "korosenai_gasputin"},
        )
        self.assertEqual(len({row["value_json"] for row in core}), 1)
        self.assertTrue(all(row["confidence"] == "verified" and
                            row["verification_status"] ==
                            "two_independent_current_version_guides"
                            for row in core))

        extras = self.connection.execute(
            """SELECT source_id, verification_status FROM claims
            WHERE subject_key='boss:gasputin'
              AND predicate='recommended_source_specific_extra'"""
        ).fetchall()
        self.assertEqual(len(extras), 4)
        self.assertTrue(all(row["verification_status"].startswith("single_")
                            for row in extras))

    def test_cp020_boss_core_links_keep_targeting_and_preparation_scope(self):
        rows = self.connection.execute(
            """SELECT advice_id, applicability_json, confidence,
                verification_status FROM checkpoint_advice
            WHERE advice_id IN ('advice_cp020_togrus_maximus',
                                'advice_cp020_slamphibians')"""
        ).fetchall()
        advice = {row["advice_id"]: row for row in rows}
        self.assertEqual(set(advice), {
            "advice_cp020_togrus_maximus", "advice_cp020_slamphibians"})
        for row in advice.values():
            applicability = json.loads(row["applicability_json"])
            claim_ids = applicability["evidence_claim_ids"]
            placeholders = ",".join("?" for _ in claim_ids)
            claims = self.connection.execute(
                f"SELECT claim_id, source_id FROM claims "
                f"WHERE claim_id IN ({placeholders})", claim_ids
            ).fetchall()
            self.assertEqual(len(claims), len(claim_ids))
            self.assertEqual(len({claim["source_id"] for claim in claims}), 2)
            self.assertEqual(row["confidence"], "verified")

        slam = json.loads(
            advice["advice_cp020_slamphibians"]["applicability_json"])
        self.assertIn("target_priority", slam["source_dispute"])
        self.assertEqual(slam["single_source_extras"]["source_publisher"],
                         "Game8")
        priorities = self.connection.execute(
            """SELECT value_json, source_id, verification_status FROM claims
            WHERE subject_key='boss:slamphibians'
              AND predicate='recommended_target_priority'"""
        ).fetchall()
        self.assertEqual(len(priorities), 3)
        self.assertEqual(len({row["value_json"] for row in priorities}), 2)
        self.assertIn("single_publisher_conflicting_guidance",
                      {row["verification_status"] for row in priorities})
        poison_id = "claim_slamphibians_poison_prep_game8"
        self.assertNotIn(poison_id, slam["evidence_claim_ids"])

    def test_intermediate_power_roles_are_two_source_and_mastery_gated(self):
        expected = {
            "advice_cp018_paladin_survival": ["Martial Artist", "Priest"],
            "advice_cp019_sailor_party_burst": [],
            "advice_cp020_armamentalist_elemental_role": ["Warrior", "Mage"],
            "advice_cp021_sage_spell_echo": ["Mage", "Priest"],
            "advice_cp023_pirate_sustain": ["Thief", "Sailor"],
        }
        for advice_id, mastery in expected.items():
            row = self.connection.execute(
                """SELECT applicability_json, confidence, verification_status
                FROM checkpoint_advice WHERE advice_id=?""", (advice_id,)
            ).fetchone()
            applicability = json.loads(row["applicability_json"])
            self.assertEqual(row["confidence"], "verified")
            self.assertIn("two_source_verified", row["verification_status"])
            self.assertEqual(applicability["requires"]["mastered"], mastery)
            claim_ids = applicability["evidence_claim_ids"]
            self.assertEqual(len(claim_ids), 2)
            placeholders = ",".join("?" for _ in claim_ids)
            claims = self.connection.execute(
                f"""SELECT value_json, source_id, verification_status
                FROM claims WHERE claim_id IN ({placeholders})""", claim_ids
            ).fetchall()
            self.assertEqual(len(claims), 2)
            self.assertEqual(len({claim["source_id"] for claim in claims}), 2)
            self.assertEqual(len({claim["value_json"] for claim in claims}), 1)
            self.assertTrue(all(
                claim["verification_status"] ==
                "two_independent_current_version_editorial_sources"
                for claim in claims))

        sailor = json.loads(self.connection.execute(
            """SELECT applicability_json FROM checkpoint_advice
            WHERE advice_id='advice_cp019_sailor_party_burst'"""
        ).fetchone()[0])
        self.assertEqual(sailor["requires"]["checkpoint_at_least"],
                         "cp_009_alltrades_abbey")
        self.assertIn("no prerequisite mastery", sailor["availability_note"])

    def test_miracle_sword_midgame_spike_is_fully_linked_without_ranking(self):
        row = self.connection.execute(
            """SELECT applicability_json, confidence, verification_status
            FROM checkpoint_advice
            WHERE advice_id='advice_cp015_miracle_sword_55'"""
        ).fetchone()
        applicability = json.loads(row["applicability_json"])
        self.assertEqual(row["confidence"], "verified")
        self.assertEqual(applicability["requires"]["mini_medals"], 55)
        self.assertEqual(applicability["verified_core"]["stats"],
                         {"attack": 100, "charm": 28})
        self.assertEqual(applicability["verified_core"]["legal_users"],
                         ["Hero", "Aishe", "Sir Mervyn"])
        self.assertIn("not a complete ranking",
                      applicability["strongest_now_scope"])
        claim_ids = applicability["evidence_claim_ids"]
        self.assertEqual(len(claim_ids), 8)
        claims = self.connection.execute(
            f"""SELECT predicate, value_json, source_id FROM claims
            WHERE claim_id IN ({','.join('?' for _ in claim_ids)})""",
            claim_ids,
        ).fetchall()
        self.assertEqual(len(claims), 8)
        for predicate in ("attack_and_charm", "attack_healing_effect",
                          "medal_reward_threshold", "equip_legal_characters"):
            matched = [claim for claim in claims
                       if claim["predicate"] == predicate]
            self.assertEqual(len(matched), 2, predicate)
            self.assertEqual(len({claim["source_id"] for claim in matched}), 2)
            self.assertEqual(len({claim["value_json"] for claim in matched}), 1)

        legality = self.connection.execute(
            """SELECT character_name, can_equip FROM equipment_compatibility
            WHERE item_id='item_miracle_sword'"""
        ).fetchall()
        allowed = {record["character_name"] for record in legality
                   if record["can_equip"]}
        self.assertEqual(allowed, {"Hero", "Aishe", "Sir Mervyn"})

    def test_cp020_liquid_metal_grind_is_two_source_and_optional(self):
        row = self.connection.execute(
            "SELECT applicability_json, confidence FROM checkpoint_advice "
            "WHERE advice_id='advice_cp020_liquid_metal_grind'"
        ).fetchone()
        applicability = json.loads(row["applicability_json"])
        self.assertEqual(row["confidence"], "verified")
        self.assertTrue(applicability["optional"])
        self.assertIn("no published numeric ceiling", applicability["ceiling"])
        ids = applicability["evidence_claim_ids"]
        claims = self.connection.execute(
            f"SELECT predicate, value_json, source_id FROM claims WHERE claim_id IN ({','.join('?' for _ in ids)})",
            ids,
        ).fetchall()
        self.assertEqual(len(claims), 4)
        for predicate in ("recommended_midgame_farm_locations",
                          "recommended_farm_tactics"):
            rows = [claim for claim in claims if claim["predicate"] == predicate]
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({claim["source_id"] for claim in rows}), 2)
            self.assertEqual(len({claim["value_json"] for claim in rows}), 1)

    def test_boss_skill_recommendations_keep_tactic_evidence_distinct(self):
        rows = self.connection.execute(
            """SELECT recommendation_verification_status,
                corroborating_source_id, corroborating_locator
            FROM boss_skill_recommendations"""
        ).fetchall()
        self.assertEqual(len(rows), 8)
        self.assertEqual(sum(row["recommendation_verification_status"] == "single_source"
                             for row in rows), 1)
        self.assertEqual(sum(row["recommendation_verification_status"] == "two_source_verified"
                             for row in rows), 7)
        self.assertTrue(all(
            (row["corroborating_source_id"] is not None and
             row["corroborating_locator"] is not None) ==
            (row["recommendation_verification_status"] == "two_source_verified")
            for row in rows
        ))

    def test_early_aqua_slash_boss_tactics_have_independent_corroboration(self):
        rows = self.connection.execute(
            """SELECT boss_name, recommendation_verification_status,
                corroborating_source_id, k.proficiency_rank,
                k.verification_status AS rank_verification_status
            FROM boss_skill_recommendations b
            JOIN vocation_rank_skills k USING(vocation_skill_id)
            WHERE b.boss_name IN ('Hackrobat', 'Slaughtomaton')
            ORDER BY boss_name"""
        ).fetchall()
        self.assertEqual([row["boss_name"] for row in rows],
                         ["Hackrobat", "Slaughtomaton"])
        self.assertTrue(all(row["recommendation_verification_status"] ==
                            "two_source_verified" for row in rows))
        self.assertEqual(
            {row["corroborating_source_id"] for row in rows},
            {"noobfeed_bosses_larca", "noobfeed_bosses_frobisher"},
        )
        self.assertEqual({row["proficiency_rank"] for row in rows}, {4})
        self.assertTrue(all(not row["rank_verification_status"].startswith("two_")
                            for row in rows))

        verified_pairs = self.connection.execute(
            """SELECT subject_key, predicate, COUNT(DISTINCT source_id) AS sources
            FROM claims
            WHERE subject_key IN ('boss:hackrobat', 'boss:slaughtomaton')
              AND verification_status='two_independent_current_version_sources'
            GROUP BY subject_key, predicate
            ORDER BY subject_key, predicate"""
        ).fetchall()
        self.assertEqual(
            {(row["subject_key"], row["predicate"], row["sources"])
             for row in verified_pairs},
            {
                ("boss:hackrobat", "recommended_damage_setup", 2),
                ("boss:hackrobat", "recommended_hero_role", 2),
                ("boss:slaughtomaton", "recommended_damage_setup", 2),
                ("boss:slaughtomaton", "recommended_hero_role", 2),
            },
        )

    def test_numpton_aooo_tactic_is_corroborated_but_rank_stays_separate(self):
        row = self.connection.execute(
            """SELECT b.recommendation_verification_status,
                b.corroborating_source_id, b.corroborating_locator,
                k.proficiency_rank, k.verification_status AS rank_status
            FROM boss_skill_recommendations b
            JOIN vocation_rank_skills k USING(vocation_skill_id)
            WHERE b.boss_name=\"Numpton's Numpties\"
              AND k.skill_name='Aooo!'"""
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["recommendation_verification_status"],
                         "two_source_verified")
        self.assertEqual(row["corroborating_source_id"],
                         "noobfeed_bosses_alltrades")
        self.assertIn("Aooo!", row["corroborating_locator"])
        self.assertEqual(row["proficiency_rank"], 4)
        self.assertFalse(row["rank_status"].startswith("two_"))

        claims = self.connection.execute(
            """SELECT source_id, value_json, verification_status
            FROM claims
            WHERE subject_key='boss:numptons_numpties'
              AND predicate='recommended_arena_plan'
            ORDER BY source_id"""
        ).fetchall()
        self.assertEqual({claim["source_id"] for claim in claims},
                         {"game8_allblades_arena", "noobfeed_bosses_alltrades"})
        self.assertEqual(len({claim["value_json"] for claim in claims}), 1)
        self.assertTrue(all(claim["verification_status"] ==
                            "two_independent_current_version_sources"
                            for claim in claims))

    def test_equipment_compatibility_requires_two_source_row_agreement(self):
        adjudicated = self.connection.execute(
            """SELECT agreement_status, allowed_characters_json,
                source_a_characters_json, source_b_characters_json
            FROM equipment_compatibility_audits
            WHERE item_id='item_liquid_metal_sword'"""
        ).fetchone()
        self.assertEqual(adjudicated["agreement_status"], "two_source_agreement")
        self.assertIsNotNone(adjudicated["allowed_characters_json"])
        self.assertNotEqual(adjudicated["source_a_characters_json"],
                            adjudicated["source_b_characters_json"])
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM equipment_compatibility WHERE item_id='item_liquid_metal_sword'"
        ).fetchone()[0], 6)
        adjudicated_conflict = self.connection.execute(
            """SELECT status, resolution_claim_id, detection_method FROM conflicts
            WHERE conflict_key LIKE 'item:liquid_metal_sword|equipment_compatible_characters|%'
              AND detection_method='two_independent_source_consensus_external_claim'
            """
        ).fetchone()
        self.assertEqual(adjudicated_conflict["status"], "resolved")
        self.assertEqual(adjudicated_conflict["resolution_claim_id"],
                         "claim_equipcompat_liquid_metal_sword_gamershigh")
        self.assertEqual(adjudicated_conflict["detection_method"],
                         "two_independent_source_consensus_external_claim")
        external_resolutions = self.connection.execute(
            """SELECT f.resolution_claim_id, resolution.subject_key,
                resolution.predicate, resolution.value_json
            FROM conflicts f
            JOIN claims resolution
              ON resolution.claim_id=f.resolution_claim_id
            WHERE f.detection_method=
              'two_independent_source_consensus_external_claim'"""
        ).fetchall()
        self.assertEqual(len(external_resolutions), 14)
        for resolution in external_resolutions:
            publishers = self.connection.execute(
                """SELECT DISTINCT s.publisher
                FROM claims c JOIN sources s ON s.source_id=c.source_id
                WHERE c.subject_key=? AND c.predicate=? AND c.value_json=?""",
                (resolution["subject_key"], resolution["predicate"],
                 resolution["value_json"]),
            ).fetchall()
            self.assertGreaterEqual(len(publishers), 2)

        iron_lance = self.connection.execute(
            """SELECT agreement_status, allowed_characters_json, source_b_id, source_c_id
            FROM equipment_compatibility_audits WHERE item_id='item_iron_lance'"""
        ).fetchone()
        self.assertEqual(iron_lance["agreement_status"], "two_source_agreement")
        self.assertEqual(json.loads(iron_lance["allowed_characters_json"]),
                         ["Hero", "Kiefer", "Ruff", "Aishe", "Sir Mervyn"])
        self.assertEqual(iron_lance["source_b_id"], "hyperwiki_equipment_spear")
        self.assertEqual(iron_lance["source_c_id"], "appmedia_iron_lance")
        retained_sources = {row[0] for row in self.connection.execute(
            """SELECT source_id FROM claims
            WHERE subject_key='item:iron_lance'
              AND predicate='equipment_compatible_characters'"""
        )}
        self.assertIn("gamers_high_equipment_weapon", retained_sources)

        cypress = self.connection.execute(
            """SELECT agreement_status FROM equipment_compatibility_audits
            WHERE item_id='item_cypress_stick'"""
        ).fetchone()
        self.assertEqual(cypress["agreement_status"], "two_source_agreement")
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM equipment_compatibility WHERE item_id='item_cypress_stick'"
        ).fetchone()[0], 6)
        self.assertTrue(all(row["status"] == "resolved" for row in self.connection.execute(
            """SELECT status FROM conflicts
            WHERE conflict_key LIKE 'item:cypress_stick|equipment_compatible_characters|%'"""
        )))

        cautery = self.connection.execute(
            """SELECT a.agreement_status, e.character_name, e.can_equip
            FROM equipment_compatibility_audits a
            JOIN equipment_compatibility e USING(item_id)
            WHERE a.item_id='item_cautery_sword'
            ORDER BY e.character_name"""
        ).fetchall()
        self.assertEqual(len(cautery), 6)
        self.assertTrue(all(row["agreement_status"] == "two_source_agreement"
                            for row in cautery))
        allowed = {row["character_name"] for row in cautery if row["can_equip"]}
        self.assertEqual(allowed, {"Hero", "Aishe", "Sir Mervyn"})
        self.assertIsNone(self.connection.execute(
            """SELECT conflict_id FROM conflicts
            WHERE conflict_key LIKE 'item:cautery_sword|equipment_compatible_characters|%'"""
        ).fetchone())

        singles = self.connection.execute(
            """SELECT item_id, source_b_id, source_c_id FROM equipment_compatibility_audits
            WHERE agreement_status='single_source' ORDER BY item_id"""
        ).fetchall()
        self.assertEqual(singles, [])

        accessory_rows = self.connection.execute(
            """SELECT a.agreement_status, COUNT(*) AS row_count
            FROM equipment_compatibility_audits a JOIN items i USING(item_id)
            JOIN item_categories c USING(category_id)
            WHERE c.name='Accessories' GROUP BY a.agreement_status"""
        ).fetchall()
        self.assertEqual({row["agreement_status"]: row["row_count"] for row in accessory_rows},
                         {"two_source_agreement": 74})
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM equipment_compatibility WHERE item_id='item_slime_heart'"
        ).fetchone()[0], 6)
        redirect = self.connection.execute(
            """SELECT canonical_item_id, verification_status FROM item_identity_redirects
            WHERE legacy_item_id='item_meowgiican_heart'"""
        ).fetchone()
        self.assertEqual(redirect["canonical_item_id"], "item_meowgician_heart")
        self.assertEqual(redirect["verification_status"],
                         "two_source_typographic_identity_resolution")
        self.assertEqual(self.counts["seed_effects"], 18)
        self.assertEqual(self.counts["seed_reward_rules"], 1)
        self.assertEqual(self.counts["shops"], 47)
        self.assertEqual(self.counts["shop_inventory"], 118)
        self.assertEqual(self.counts["lucky_panel_pools"], 14)
        self.assertEqual(self.counts["lucky_panel_rules"], 1)
        self.assertEqual(self.counts["lucky_panel_rewards"], 302)
        self.assertEqual(self.counts["stone_tablets"], 20)
        self.assertEqual(self.counts["tablet_fragments"], 71)
        self.assertEqual(self.counts["monsters"], 333)
        self.assertEqual(self.counts["vicious_targets"], 10)
        self.assertEqual(self.counts["vicious_encounters"], 11)
        self.assertEqual(self.counts["achievements"], 61)
        self.assertEqual(self.counts["achievement_aliases"], 1)
        self.assertEqual(self.counts["achievement_requirements"], 29)
        self.assertEqual(self.counts["vocation_rank_costs"], 163)
        self.assertEqual(self.counts["vocation_progression_profiles"], 26)

    def test_achievement_registry_is_complete_and_checkpoint_scoped(self):
        counts = dict(
            self.connection.execute(
                "SELECT category, COUNT(*) FROM achievements GROUP BY category"
            ).fetchall()
        )
        self.assertEqual(counts, {"actionable": 28, "meta": 1, "story": 32})
        invalid = self.connection.execute(
            """SELECT achievement_id FROM achievements
            WHERE length(trim(locator)) = 0 OR source_id IS NULL"""
        ).fetchall()
        self.assertEqual(invalid, [])
        alias = self.connection.execute(
            """SELECT achievement_id, alias FROM achievement_aliases
            WHERE alias_id = 'ach_alias_field_day_a_questrian'"""
        ).fetchone()
        self.assertEqual(tuple(alias), ("ach_field_day", "A Questrian"))

    def test_achievement_requirements_cover_every_non_story_achievement(self):
        missing = self.connection.execute(
            """SELECT a.achievement_id FROM achievements a
            LEFT JOIN achievement_requirements r USING(achievement_id)
            WHERE a.category != 'story' AND r.requirement_id IS NULL"""
        ).fetchall()
        self.assertEqual(missing, [])
        unresolved = self.connection.execute(
            """SELECT COUNT(*) FROM achievement_requirements
            WHERE target_type = 'unresolved_registry'"""
        ).fetchone()[0]
        self.assertEqual(unresolved, 0)
        hoarder = self.connection.execute(
            """SELECT required_count FROM achievement_requirements
            WHERE achievement_id = 'ach_heroic_hoarder'"""
        ).fetchone()[0]
        self.assertEqual(hoarder, 353)

    def test_cumulative_achievement_semantics_resolve_gold_and_metal_roster(self):
        statuses = dict(self.connection.execute(
            """SELECT target_key, verification_status
            FROM achievement_requirements
            WHERE target_type='action_counter'"""
        ).fetchall())
        self.assertIn("individual_monsters", statuses["monsters_defeated"])
        self.assertIn("individual_metal_family_members",
                      statuses["metal_monsters_defeated"])
        self.assertIn("quick_win_exclusion_two_publishers",
                      statuses["battles_won"])
        self.assertIn("successful_quick_win_event_unit_two_publishers",
                      statuses["quick_wins_earned"])
        self.assertIn("lifetime_total_semantics", statuses["gold_acquired"])
        self.assertIn("roster_verified", statuses["metal_monsters_defeated"])

        gold = self.connection.execute(
            """SELECT status, claim_a_id, claim_b_id FROM conflicts
            WHERE conflict_key LIKE
              'achievement:massively_minted|achievement_counter_condition|%'"""
        ).fetchone()
        self.assertEqual(gold["status"], "resolved")
        self.assertEqual(
            {gold["claim_a_id"], gold["claim_b_id"]},
            {"claim_massively_minted_lifetime_gold_maestros",
             "claim_massively_minted_current_balance_steam_guide"},
        )
        resolution = self.connection.execute(
            """SELECT resolution_claim_id FROM conflicts
            WHERE conflict_key LIKE
              'achievement:massively_minted|achievement_counter_condition|%'"""
        ).fetchone()[0]
        self.assertEqual(resolution,
                         "claim_massively_minted_lifetime_gold_maestros")
        consensus_publishers = self.connection.execute(
            """SELECT COUNT(DISTINCT s.publisher)
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='achievement:massively_minted'
              AND c.predicate='achievement_counter_condition'
              AND c.value_json='\"lifetime total gold acquired\"'"""
        ).fetchone()[0]
        self.assertEqual(consensus_publishers, 4)
        roster_publishers = self.connection.execute(
            """SELECT COUNT(DISTINCT s.publisher)
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='achievement:metal_mangler'
              AND c.predicate='achievement_counter_members'"""
        ).fetchone()[0]
        self.assertEqual(roster_publishers, 2)

        units = self.connection.execute(
            """SELECT c.subject_key, c.predicate, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.claim_id IN (
              'claim_winning_machine_battle_unit_altema',
              'claim_monster_masher_individual_unit_altema',
              'claim_metal_mangler_individual_family_unit_altema',
              'claim_loose_cannon_partywide_maestros')"""
        ).fetchall()
        self.assertEqual(len(units), 4)
        self.assertEqual({row["publisher"] for row in units},
                         {"Altema", "Maestros del Mando"})

        exclusion_publishers = self.connection.execute(
            """SELECT COUNT(DISTINCT s.publisher)
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='achievement:winning_machine'
              AND c.predicate='achievement_counter_exclusion'
              AND c.value_json='"field-attack instant kills do not count as battle wins"'"""
        ).fetchone()[0]
        self.assertEqual(exclusion_publishers, 2)

        quick_units = self.connection.execute(
            """SELECT c.value_json, c.locator, s.publisher, s.url
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='achievement:straight_to_the_point'
              AND c.predicate='achievement_counter_unit'"""
        ).fetchall()
        self.assertEqual(len(quick_units), 2)
        self.assertEqual(len({row["publisher"] for row in quick_units}), 2)
        self.assertEqual({json.loads(row["value_json"]) for row in quick_units},
                         {"successful field-attack instant-kill events"})
        self.assertTrue(all(row["locator"] and row["url"].startswith("https://")
                            for row in quick_units))

        detailed = self.connection.execute(
            """SELECT c.value_json, c.locator, s.url
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.claim_id='claim_detailed_records_counter_registry_dq_dictionary'"""
        ).fetchone()
        self.assertEqual(set(json.loads(detailed["value_json"])), {
            "battle wins", "monsters defeated", "field attacks", "quick wins",
            "metal-family monsters defeated",
        })
        self.assertIn("lines 117-134", detailed["locator"])
        self.assertTrue(detailed["url"].startswith("https://"))

    def test_troll_heart_false_repeatable_drop_is_visible_and_resolved(self):
        claims = self.connection.execute(
            """SELECT c.claim_id, c.value_json, c.confidence, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='item:troll_heart'
              AND c.predicate='acquisition_method'"""
        ).fetchall()
        self.assertEqual(len(claims), 3)
        self.assertEqual(sum("field sparkle" in json.loads(row["value_json"])
                             for row in claims), 2)
        losing = next(row for row in claims if row["publisher"] == "XboxPlay")
        self.assertEqual(losing["confidence"], "low")
        self.assertIn("respawning", json.loads(losing["value_json"]))

        conflicts = self.connection.execute(
            """SELECT status, resolution_claim_id, rationale
            FROM conflicts
            WHERE conflict_key LIKE 'item:troll_heart|acquisition_method|%'"""
        ).fetchall()
        self.assertEqual(len(conflicts), 2)
        self.assertTrue(all(row["status"] == "resolved" for row in conflicts))
        self.assertTrue(all("field_sparkle" in row["resolution_claim_id"]
                            for row in conflicts))
        self.assertTrue(all("second copy" in row["rationale"]
                            for row in conflicts))

    def test_achievement_report_uses_only_explicit_player_progress(self):
        report = load_achievement_report(
            self.db_path, ROOT / "player" / "ryan-save-state.json"
        )
        self.assertEqual(report["total"], 61)
        self.assertEqual(report["unlocked_count"], 0)
        self.assertEqual(len(report["achievements"]), 61)
        by_id = {row["achievement_id"]: row for row in report["achievements"]}
        for achievement_id in ("ach_heroic_hoarder", "ach_take_no_prisoners",
                               "ach_vanquisher_of_the_vicious",
                               "ach_no_stone_left_unturned", "ach_master_of_all"):
            self.assertIsNone(by_id[achievement_id]["progress"])
            self.assertEqual(by_id[achievement_id]["dependency_progress"]["status"],
                             "unknown")

        state_path = Path(self.tempdir.name) / "achievement-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["achievements_unlocked"] = [
            "ach_into_the_unknown", "unknown_legacy_name"
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_achievement_report(self.db_path, state_path)
        self.assertEqual(report["unlocked_count"], 1)
        self.assertEqual(report["unknown_state_ids"], ["unknown_legacy_name"])
        self.assertEqual(len(report["achievements"]), 60)

    def test_achievement_dependencies_count_only_explicit_identifiers(self):
        state_path = Path(self.tempdir.name) / "achievement-dependencies.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["items_obtained"] = ["item_cypress_stick"]
        state["completion"]["monster_entries"] = ["monster_001"]
        state["completion"]["tablet_fragments"] = ["fragment_land_pilchard_bay_1"]
        state["completion"]["mini_medal_count"] = 0
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_achievement_report(self.db_path, state_path, True)
        by_id = {row["achievement_id"]: row for row in report["achievements"]}
        self.assertEqual(by_id["ach_heroic_hoarder"]["progress"], 1)
        self.assertEqual(by_id["ach_heroic_hoarder"]["dependency_progress"]["status"],
                         "partial")
        self.assertEqual(by_id["ach_take_no_prisoners"]["progress"], 1)
        self.assertEqual(by_id["ach_gold_medallist"]["progress"], 0)
        self.assertEqual(by_id["ach_gold_medallist"]["dependency_progress"]["status"],
                         "partial")

    def test_player_progress_records_and_reopens_achievements(self):
        state_path = Path(self.tempdir.name) / "achievement-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "achievement-unlocked", ["ach_into_the_unknown"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["achievements_unlocked"], ["ach_into_the_unknown"]
        )
        update_progress(
            state_path, self.db_path, "achievement-undo", ["ach_into_the_unknown"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["achievements_unlocked"], [])
        with self.assertRaisesRegex(ValueError, "Unknown achievement"):
            update_progress(
                state_path, self.db_path, "achievement-unlocked", ["ach_not_real"]
            )

    def test_every_claim_has_registered_source(self):
        orphans = self.connection.execute(
            """SELECT c.claim_id FROM claims c
            LEFT JOIN sources s ON s.source_id = c.source_id
            WHERE s.source_id IS NULL"""
        ).fetchall()
        self.assertEqual(orphans, [])

    def test_all_hoarder_category_identities_are_complete(self):
        counts = dict(
            self.connection.execute(
                """SELECT c.name, COUNT(*) FROM items i
                JOIN item_categories c USING(category_id)
                WHERE i.heroic_hoarder_required = 1
                GROUP BY c.name"""
            ).fetchall()
        )
        self.assertEqual(
            counts,
            {
                "Accessories": 74,
                "Armour": 69,
                "Head": 33,
                "Shields": 24,
                "Usable Items": 43,
                "Weapons": 110,
            },
        )
        gaps = self.connection.execute(
            """SELECT COUNT(*) FROM items i
            LEFT JOIN item_acquisition_paths a USING(item_id)
            WHERE a.item_id IS NULL"""
        ).fetchone()[0]
        unexplained_gaps = self.connection.execute(
            """SELECT item_id FROM items i
            LEFT JOIN item_acquisition_paths a USING(item_id)
            WHERE a.item_id IS NULL
              AND i.verification_status NOT LIKE 'source_checked_route_gap%'"""
        ).fetchall()
        self.assertEqual(gaps, 0)
        self.assertEqual(unexplained_gaps, [])

    def test_monster_heart_batch_preserves_known_and_unknown_availability(self):
        golem = self.connection.execute(
            """SELECT effect_text, available_from_checkpoint_id, locator
            FROM monster_hearts WHERE heart_id = 'heart_golem'"""
        ).fetchone()
        self.assertEqual(golem[1], "cp_003_ballymolloy")
        self.assertIn("survive a killing blow", golem[0])
        self.assertIn("Golem Heart for Survivability", golem[2])
        unknown = self.connection.execute(
            """SELECT COUNT(*) FROM monster_hearts
            WHERE available_from_checkpoint_id IS NULL"""
        ).fetchone()[0]
        self.assertEqual(unknown, 39)
        missing_provenance = self.connection.execute(
            """SELECT COUNT(*) FROM monster_hearts h
            LEFT JOIN sources s USING(source_id)
            WHERE s.source_id IS NULL OR trim(h.locator) = ''"""
        ).fetchone()[0]
        self.assertEqual(missing_provenance, 0)
        dlc_scoped = self.connection.execute(
            """SELECT name FROM monster_hearts
            WHERE dlc_scope = 'Jam-Packed Swag Bag'
            ORDER BY name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in dlc_scoped],
            ["Gold Golem Heart", "Metal Slime Heart"],
        )
        self.assertEqual(self.connection.execute(
            """SELECT COUNT(*) FROM monster_hearts
            WHERE dlc_scope IS NOT NULL AND dlc_source_id IS NOT NULL
              AND trim(dlc_locator) <> ''"""
        ).fetchone()[0], 5)
        dlc_arena_routes = self.connection.execute(
            """SELECT name, availability_notes, availability_source_id,
                availability_locator, available_from_checkpoint_id,
                verification_status
            FROM monster_hearts
            WHERE name IN ('Dragonlord Heart', 'Malroth Heart', 'Zoma Heart')
            ORDER BY name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in dlc_arena_routes],
            ["Dragonlord Heart", "Malroth Heart", "Zoma Heart"],
        )
        self.assertTrue(all("DLC-only Buccanham Palace Battle Arena" in row[1] for row in dlc_arena_routes))
        self.assertTrue(all(row[2] == "ngb_monster_hearts" for row in dlc_arena_routes))
        self.assertTrue(all("> How to Obtain" in row[3] for row in dlc_arena_routes))
        self.assertTrue(all(row[4] == "cp_020_buccanham" for row in dlc_arena_routes))
        self.assertTrue(all(row[5] == "cross_source_checked_dlc_route_checkpoint_gated" for row in dlc_arena_routes))

    def test_meowgician_heart_has_direct_finite_vicious_route(self):
        row = self.connection.execute(
            """SELECT i.heroic_hoarder_required, a.method, a.location_text,
                a.available_from_checkpoint_id, a.supply_type, a.finite_total,
                a.is_free, a.verification_status
            FROM items i JOIN item_acquisition_paths a USING(item_id)
            WHERE i.name = 'Meowgician Heart'"""
        ).fetchone()
        self.assertEqual(tuple(row[:7]), (0, "drop", "L'Arca", "cp_005_larca", "finite", 1, 1))
        self.assertIn("repeatability_unproven", row[7])

    def test_early_panel_items_have_direct_free_fixed_alternatives(self):
        rows = self.connection.execute(
            """SELECT item_id, available_from_checkpoint_id, supply_type,
                finite_total, is_free, prerequisite_json
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_pretty_betsy_larca_region_present',
                'acq_prayer_ring_tunnel_to_abbey_past'
            ) ORDER BY item_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_item = {row["item_id"]: row for row in rows}
        self.assertEqual(by_item["item_pretty_betsy"]["available_from_checkpoint_id"], "cp_005_larca")
        self.assertEqual(
            json.loads(by_item["item_pretty_betsy"]["prerequisite_json"])["access"],
            "land directly by boat",
        )
        self.assertEqual(by_item["item_prayer_ring"]["available_from_checkpoint_id"], "cp_009_alltrades")
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))

    def test_early_helmet_pages_add_finite_free_routes(self):
        rows = self.connection.execute(
            """SELECT acquisition_id, available_from_checkpoint_id, supply_type,
                finite_total, is_free, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_leather_hat_pilchard_bay_present',
                'acq_leather_hat_estard_present',
                'acq_pointy_hat_rainbow_mines_past',
                'acq_hardwood_headwear_ballymolloy_present'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(rows), 4)
        by_id = {row["acquisition_id"]: row for row in rows}
        self.assertEqual(
            by_id["acq_leather_hat_pilchard_bay_present"]["available_from_checkpoint_id"],
            "cp_001_prologue",
        )
        self.assertEqual(
            by_id["acq_hardwood_headwear_ballymolloy_present"]["available_from_checkpoint_id"],
            "cp_003_ballymolloy",
        )
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["verification_status"] == "source_checked_exact_container"
                            for row in rows))

    def test_early_armour_pages_add_finite_free_routes(self):
        rows = self.connection.execute(
            """SELECT acquisition_id, available_from_checkpoint_id, supply_type,
                finite_total, is_free, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_noble_garb_institute_past',
                'acq_silk_robe_bandits_base_present'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_id = {row["acquisition_id"]: row for row in rows}
        self.assertEqual(
            by_id["acq_noble_garb_institute_past"]["available_from_checkpoint_id"],
            "cp_007_frobisher",
        )
        self.assertEqual(
            by_id["acq_silk_robe_bandits_base_present"]["available_from_checkpoint_id"],
            "cp_010_alltrades_present",
        )
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["verification_status"] == "source_checked_exact_container"
                            for row in rows))

    def test_early_accessory_routes_are_direct_and_container_safe(self):
        rows = self.connection.execute(
            """SELECT acquisition_id, method, location_text,
                available_from_checkpoint_id, supply_type, is_free,
                verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_rabbit_tail_grotto_silgillo',
                'acq_fishnet_stockings_frobisher_past'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_id = {row["acquisition_id"]: row for row in rows}
        rabbit = by_id["acq_rabbit_tail_grotto_silgillo"]
        self.assertEqual(tuple(rabbit[1:4]), (
            "chest", "Grotta del Sigillo Level 3", "cp_005_larca"
        ))
        self.assertIn("exact_container", rabbit["verification_status"])
        fishnet = by_id["acq_fishnet_stockings_frobisher_past"]
        self.assertEqual(fishnet["available_from_checkpoint_id"], "cp_007_frobisher")
        self.assertEqual(fishnet["method"], "other")
        self.assertEqual(fishnet["location_text"], "Frobisher inn right-hand room")
        self.assertIn("resolved_present_exact_container",
                      fishnet["verification_status"])
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))

    def test_kamikazee_bracer_has_cp011_fixed_free_alternative(self):
        row = self.connection.execute(
            """SELECT method, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total,
                is_free, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id = 'acq_kamikazee_bracer_likeness_great_evil_past'"""
        ).fetchone()
        self.assertEqual(tuple(row[:7]), (
            "chest", "Likeness of the Great Evil 5F", "Past",
            "cp_011_la_bravoure", "finite", 1, 1,
        ))
        self.assertEqual(row[7], "two_source_route_exact_container_resolved")

    def test_missables_have_precise_provenance_and_exact_blue_button_cutoff(self):
        rows = self.connection.execute(
            """SELECT missable_id, unavailable_after, consequence, locator
            FROM missables ORDER BY missable_id"""
        ).fetchall()
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row[3] and ">" in row[3] for row in rows))
        unknown = {row[0] for row in rows if row[1] is None}
        self.assertEqual(unknown, set())
        blue_button = next(row for row in rows
                           if row[0] == "missable_blue_button")
        self.assertIn("Cataclysm", blue_button[1])
        wooden_doll = next(row for row in rows
                           if row[0] == "missable_wooden_doll")
        self.assertIn("Patrick choice", wooden_doll[1])
        vogograd = next(row for row in rows if row[0] == "missable_vogograd_tablet")
        self.assertIn("Pretty Betsy", vogograd[2])
        self.assertNotIn("Seed of Therapeusis", vogograd[2])
        links = self.connection.execute(
            """SELECT COUNT(*), COUNT(obligation_id)
            FROM missables WHERE available_from_checkpoint_id IS NOT NULL"""
        ).fetchone()
        self.assertEqual(tuple(links), (7, 7))

        blue_stop = self.connection.execute(
            """SELECT stop_before_advancing FROM checkpoint_obligations
            WHERE obligation_id='obl_emberdale_blue_button_deadline'"""
        ).fetchone()[0]
        self.assertEqual(blue_stop, 0)
        final_warning = self.connection.execute(
            """SELECT checkpoint_id, stop_before_advancing, verification_status
            FROM checkpoint_obligations
            WHERE obligation_id='obl_almighty_blue_button_final_warning'"""
        ).fetchone()
        self.assertEqual(tuple(final_warning),
                         ("cp_022_almighty", 1,
                          "continuous_walkthrough_direct_checkpoint_mapping_cutoff_two_source_verified"))

    def test_farming_rows_are_checkpoint_gated_and_strategy_attributed(self):
        rows = self.connection.execute(
            """SELECT farming_id, available_from_checkpoint_id,
                encounter_rate_text, strategy, source_id, locator,
                strategy_source_id, strategy_locator
            FROM farming_spots ORDER BY farming_id"""
        ).fetchall()
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(row[1] for row in rows))
        self.assertTrue(all(row[4] and row[5] for row in rows))
        self.assertTrue(all(not row[3] or (row[6] and row[7]) for row in rows))
        self.assertTrue(all(
            row[2] is None or "no numeric encounter rate published" in row[2]
            or "no proficiency-per-time rate is published" in row[2]
            or "no gold-per-time or prize-value rate is published" in row[2]
            or "no cross-platform reset guarantee" in row[2]
            or "selection weights and reward-per-time remain unpublished" in row[2]
            for row in rows
        ))
        gold = next(row for row in rows
                    if row[0] == "farm_gold_lucky_panel_pilgrims_rest")
        self.assertEqual(gold[1], "cp_009_alltrades")
        self.assertEqual(gold[4], "rpgsite_lucky_panel")
        self.assertEqual(gold[6], "game8_gold_farming")
        proficiency = next(row for row in rows
                           if row[0] == "farm_vocation_proficiency_highendreigh")
        self.assertEqual(proficiency[1], "cp_013_flying_carpet")
        self.assertEqual(proficiency[4], "game8_proficiency_farming")
        self.assertEqual(proficiency[6], "game8_proficiency_farming")
        seed = next(row for row in rows if row[0] == "farm_super_seeds_almighty")
        self.assertEqual(seed[1], "cp_032_yet_another_world")
        self.assertEqual(seed[4], "gamewith_super_seed_pool")
        self.assertEqual(seed[6], "game8_party_builds")

    def test_no_finite_monster_heart_reward_is_mislabeled_as_a_farm(self):
        heart_farms = self.connection.execute(
            "SELECT COUNT(*) FROM farming_spots WHERE lower(target) LIKE '%heart%'"
        ).fetchone()[0]
        self.assertEqual(heart_farms, 0)
        heart_drops = self.connection.execute(
            """SELECT DISTINCT a.supply_type
            FROM item_acquisition_paths a
            JOIN items i USING(item_id)
            WHERE i.name LIKE '% Heart' AND a.method='drop'"""
        ).fetchall()
        self.assertEqual({row[0] for row in heart_drops}, {"finite"})

    def test_seed_effects_and_reward_membership_are_verified_but_weights_unknown(self):
        rows = self.connection.execute(
            """SELECT item_id, stat_key, increase_amount, locator
            FROM seed_effects ORDER BY item_id"""
        ).fetchall()
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(row[2] > 0 and row[3] for row in rows))
        strength = next(row for row in rows if row[0] == "item_seed_of_strength")
        super_strength = next(
            row for row in rows if row[0] == "item_super_seed_of_strength"
        )
        self.assertEqual((strength[1], strength[2]), ("strength", 2))
        self.assertEqual((super_strength[1], super_strength[2]), ("strength", 20))
        reward = self.connection.execute(
            """SELECT available_from_checkpoint_id, reward_quantity,
                selection_method, eligible_items_json, repeatable
            FROM seed_reward_rules
            WHERE seed_reward_rule_id = 'seed_reward_almighty_spirits_rematch'"""
        ).fetchone()
        self.assertEqual(tuple(reward[:3]),
                         ("cp_032_yet_another_world", 1, "random"))
        eligible = json.loads(reward[3])
        self.assertEqual(len(eligible), 9)
        self.assertIn("item_super_pretty_betsy", eligible)
        self.assertEqual(reward[4], 1)
        pool_claims = self.connection.execute(
            """SELECT DISTINCT s.publisher FROM claims c
            JOIN sources s USING(source_id)
            WHERE c.subject_key='reward:almighty_spirits_rematch'
              AND c.predicate='eligible_reward_pool'"""
        ).fetchall()
        self.assertEqual({row[0] for row in pool_claims},
                         {"GameWith", "Game8 Japan"})

    def test_priority_source_tables_expose_locator_completeness(self):
        for table in ("medal_rewards", "vocations", "vocation_requirements"):
            missing = self.connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE locator IS NULL OR trim(locator) = ''"
            ).fetchone()[0]
            self.assertEqual(missing, 0, table)
        checkpoint_counts = self.connection.execute(
            """SELECT COUNT(*), SUM(locator IS NULL),
                SUM(coverage_status NOT LIKE '%partial%')
            FROM checkpoints"""
        ).fetchone()
        self.assertEqual(tuple(checkpoint_counts), (33, 0, 0))
        verified_checkpoint_locators = self.connection.execute(
            """SELECT sequence_no, locator FROM checkpoints
            ORDER BY sequence_no"""
        ).fetchall()
        self.assertEqual(len(verified_checkpoint_locators), 33)
        self.assertTrue(all(row["locator"] for row in verified_checkpoint_locators))
        self.assertIn(
            "Buccanham Arena",
            verified_checkpoint_locators[-1]["locator"],
        )
        requirement = self.connection.execute(
            """SELECT locator FROM vocation_requirements
            WHERE requirement_id = 'req_gladiator_01'"""
        ).fetchone()[0]
        self.assertIn("Gladiator", requirement)
        self.assertIn("Warrior prerequisite", requirement)

    def test_hoarder_report_preserves_unknown_progress_and_route_gaps(self):
        report = load_hoarder_report(
            self.db_path, ROOT / "player" / "ryan-save-state.json", gaps_only=True
        )
        self.assertEqual(report["total"], 353)
        self.assertEqual(report["obtained_count"], 0)
        self.assertEqual(report["routed_count"], 353)
        self.assertEqual(len(report["items"]), 0)

    def test_item_alias_preserves_losing_name_after_direct_ui_resolution(self):
        item, routes = load_item_routes(self.db_path, "Stella Fan")
        self.assertEqual(item["name"], "Stellar Fan")
        self.assertTrue(any(route["method"] == "shop" for route in routes))
        conflict = self.connection.execute(
            """SELECT 1 FROM conflicts c
            JOIN claims a ON a.claim_id = c.claim_a_id
            WHERE c.status = 'resolved'
              AND a.subject_key = 'item:stella_fan'
              AND a.predicate = 'item_display_name'"""
        ).fetchone()
        self.assertIsNotNone(conflict)
        unresolved = self.connection.execute(
            """SELECT conflict_key FROM conflicts
            WHERE status='unresolved'"""
        ).fetchall()
        self.assertEqual(len(unresolved), 0)

    def test_rampaging_encounters_have_exact_verified_road_rounds(self):
        rows = self.connection.execute(
            """SELECT e.encounter_id, m.english_name, e.location_text,
                e.source_id, e.verification_status
            FROM monster_encounters e JOIN monsters m USING(monster_id)
            WHERE e.encounter_id LIKE 'enc_rampaging_%_rampage_roads'"""
        ).fetchall()
        self.assertEqual(len(rows), 34)
        self.assertTrue(all("Round" in row["location_text"] for row in rows))
        self.assertTrue(all("category unresolved" not in row["location_text"]
                            for row in rows))
        sunken = next(row for row in rows
                      if row["english_name"] == "Rampaging Sunken Spirit")
        self.assertEqual(sunken["location_text"],
                         "Simmering Road Round 3 (Buccanham Arena)")
        self.assertIn("three_independent", sunken["verification_status"])
        summons = [row for row in rows if row["english_name"] in {
            "Rampaging Miry Hand", "Rampaging Miry Mudraker"
        }]
        self.assertEqual(len(summons), 2)
        self.assertTrue(all("summoned by" in row["location_text"]
                            for row in summons))
        conflicts = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE conflict_key LIKE
                'arena:simmering_road_round_3|starting_roster|%'"""
        ).fetchall()
        self.assertEqual(len(conflicts), 2)
        self.assertTrue(all(row["status"] == "resolved" for row in conflicts))

    def test_fixed_monster_hearts_have_two_source_exact_chests(self):
        expected = {
            "acq_slime_heart_rainbow_mines": ("B5", "northeast"),
            "acq_golem_heart_the_tower": ("5F", "Red Fragment"),
            "acq_goon_heart_cave_leading_to_the_dungeon":
                ("B2", "south branch"),
            "acq_very_devil_heart_falls_hollow":
                ("1F", "second room", "north"),
        }
        for acquisition_id, fragments in expected.items():
            route = self.connection.execute(
                """SELECT route_label, location_text, prerequisite_json,
                    source_id, verification_status
                FROM item_acquisition_paths WHERE acquisition_id=?""",
                (acquisition_id,),
            ).fetchone()
            combined = " ".join((route["route_label"], route["location_text"],
                                 route["prerequisite_json"]))
            self.assertTrue(all(fragment in combined for fragment in fragments))
            self.assertEqual(route["source_id"], "rpgsite_walkthrough")
            self.assertIn("two_independent", route["verification_status"])
            publishers = self.connection.execute(
                """SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.subject_key=?
                  AND c.predicate='precise_location_description'""",
                (f"acquisition:{acquisition_id}",),
            ).fetchall()
            self.assertEqual({row["publisher"] for row in publishers},
                             {"RPG Site", "Neoseeker"})

    def test_direct_item_pages_resolve_verified_panel_name_variants(self):
        aliases = dict(self.connection.execute(
            """SELECT alias, item_id FROM item_aliases
            WHERE alias IN ('Slime Earrings', 'Magic Vestment', 'Faerie Foil')"""
        ).fetchall())
        self.assertEqual(aliases, {
            "Slime Earrings": "item_slime_earring",
            "Magic Vestment": "item_magic_vetment",
            "Faerie Foil": "item_fairie_foil",
        })
        expected_routes = {
            "item_slime_earring": 2,
            "item_magic_vetment": 3,
            "item_fairie_foil": 2,
        }
        for item_id, expected in expected_routes.items():
            count = self.connection.execute(
                """SELECT COUNT(*) FROM item_acquisition_paths
                WHERE item_id = ? AND method = 'lucky_panel'
                  AND verification_status LIKE '%name_resolution%'""",
                (item_id,),
            ).fetchone()[0]
            self.assertEqual(count, expected)

    def test_direct_item_pages_add_finite_free_alternatives_to_panel_routes(self):
        rows = self.connection.execute(
            """SELECT item_id, time_period, available_from_checkpoint_id,
                supply_type, finite_total, is_free, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_hairband_treasure_larca_past',
                'acq_rabbit_ears_treasure_larca_present',
                'acq_coagulant_treasure_hubble_castle_past'
            ) ORDER BY item_id"""
        ).fetchall()
        self.assertEqual(len(rows), 3)
        by_item = {row["item_id"]: row for row in rows}
        self.assertEqual(by_item["item_hairband"]["available_from_checkpoint_id"], "cp_005_larca")
        self.assertEqual(by_item["item_rabbit_ears"]["time_period"], "Present")
        self.assertEqual(by_item["item_coagulant"]["available_from_checkpoint_id"], "cp_016_hubble")
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertEqual(by_item["item_hairband"]["verification_status"],
                         "source_checked_exact_container")
        self.assertEqual(by_item["item_rabbit_ears"]["verification_status"],
                         "source_checked_exact_container")
        self.assertEqual(by_item["item_coagulant"]["verification_status"],
                         "two_source_route_exact_container_resolved")
        coagulant = self.connection.execute(
            """SELECT method, route_label, location_text, prerequisite_json
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_coagulant_treasure_hubble_castle_past'"""
        ).fetchone()
        self.assertEqual(coagulant["method"], "other")
        self.assertIn("Inquisitory lower-roof barrel", coagulant["route_label"])
        self.assertNotIn("Castle", coagulant["location_text"])
        self.assertEqual(json.loads(coagulant["prerequisite_json"])["container"],
                         "barrel")

        fur_cape = self.connection.execute(
            """SELECT location_text, prerequisite_json, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_fur_cape_poolside_cave_present'"""
        ).fetchone()
        self.assertEqual(fur_cape["verification_status"],
                         "source_checked_exact_container")
        self.assertIn("northeast terminal alcove", fur_cape["location_text"])
        self.assertEqual(json.loads(fur_cape["prerequisite_json"])["container"],
                         "lone treasure chest")

    def test_late_panel_only_helmets_have_finite_free_alternatives(self):
        rows = self.connection.execute(
            """SELECT acquisition_id, item_id, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total, is_free,
                source_id, locator, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_pirates_hat_buccanham_palace_closet',
                'acq_steel_helmet_rucker_castle_past'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_item = {row["item_id"]: row for row in rows}
        pirate = by_item["item_pirates_hat"]
        self.assertEqual(
            (pirate["location_text"], pirate["time_period"],
             pirate["available_from_checkpoint_id"]),
            ("Buccanham Palace 2F bedroom", "Past", "cp_020_buccanham"),
        )
        self.assertIn("wardrobe", pirate["locator"].lower())
        steel = by_item["item_steel_helmet"]
        self.assertEqual(
            (steel["location_text"], steel["time_period"],
             steel["available_from_checkpoint_id"]),
            ("Rucker Castle 2F east room", "Past", "cp_027_deja_vous_rucker"),
        )
        self.assertEqual(steel["verification_status"],
                         "direct_pc_english_video_exact_container")
        self.assertIn("east/right chest", steel["locator"])
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["source_id"] and row["locator"] for row in rows))

    def test_video_observations_resolve_five_exact_container_members(self):
        expected = {
            "acq_dragon_shield_treasure_la_bravoure_present": "northmost/top chest",
            "acq_pirates_hat_buccanham_palace_closet": "west/left wardrobe",
            "acq_silk_robe_temple_palace_present": "east/right wardrobe",
            "acq_steel_helmet_rucker_castle_past": "east/right chest",
            "acq_knuckledusters_pilgrims_perdition_past": "east/right closet",
        }
        placeholders = ",".join("?" for _ in expected)
        rows = self.connection.execute(
            f"""SELECT acquisition_id, prerequisite_json, source_id, locator,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id IN ({placeholders})""",
            tuple(expected),
        ).fetchall()
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertTrue(row["source_id"].startswith(
                ("lordfenton_", "baigaming_")))
            self.assertIn("direct_", row["verification_status"])
            self.assertIn("english_video_exact_container",
                          row["verification_status"])
            container = json.loads(row["prerequisite_json"])["container"]
            self.assertIn(expected[row["acquisition_id"]], container)
            self.assertRegex(row["locator"], r"\d\d:\d\d")

    def test_garter_and_slime_earring_have_non_panel_alternatives(self):
        garter = self.connection.execute(
            """SELECT method, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total, is_free,
                verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_garter_greenthumb_region_present'"""
        ).fetchone()
        self.assertEqual(
            tuple(garter[:7]),
            ("other", "Wilted Heart Mayor's House 2F", "Present",
             "cp_015_greenthumb", "finite", 1, 1),
        )
        self.assertEqual(garter[7], "source_checked_exact_container")

        drops = self.connection.execute(
            """SELECT location_text, time_period, available_from_checkpoint_id,
                supply_type, finite_total, is_free, source_id, locator,
                verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_slime_earring_seaslime_drop',
                'acq_slime_earring_slimecicle_drop'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(drops), 2)
        self.assertEqual({row["location_text"] for row in drops}, {"Falls Hollow", "Coral Cave"})
        self.assertTrue(all(row["supply_type"] == "renewable" for row in drops))
        self.assertTrue(all(row["finite_total"] is None for row in drops))
        self.assertTrue(all(row["is_free"] == 1 for row in drops))
        self.assertTrue(all(row["source_id"] and row["locator"] for row in drops))
        self.assertTrue(all("rate_unknown" in row["verification_status"] for row in drops))

    def test_early_and_midgame_equipment_has_direct_finite_routes(self):
        acquisition_ids = (
            "acq_strength_ring_faraday_castle_past",
            "acq_strength_ring_mountain_path_wilted_present",
            "acq_divine_dagger_burnmont_past",
            "acq_scale_armour_burnmont_past",
            "acq_scale_armour_frobisher_past",
        )
        placeholders = ",".join("?" for _ in acquisition_ids)
        rows = self.connection.execute(
            f"""SELECT acquisition_id, item_id, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total, is_free,
                source_id, locator, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN ({placeholders}) ORDER BY acquisition_id""",
            acquisition_ids,
        ).fetchall()
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["source_id"] and row["locator"] for row in rows))
        gates = {row["acquisition_id"]: row["available_from_checkpoint_id"] for row in rows}
        self.assertEqual(gates["acq_divine_dagger_burnmont_past"], "cp_004_emberdale")
        self.assertEqual(gates["acq_scale_armour_frobisher_past"], "cp_007_frobisher")
        self.assertEqual(
            gates["acq_strength_ring_mountain_path_wilted_present"],
            "cp_015_greenthumb",
        )
        burnmont_scale = next(
            row for row in rows if row["acquisition_id"] == "acq_scale_armour_burnmont_past"
        )
        self.assertEqual(burnmont_scale["verification_status"], "source_checked_exact_chest")

    def test_knuckledusters_identity_and_first_half_fixed_routes_are_normalized(self):
        item = self.connection.execute(
            """SELECT heroic_hoarder_required, source_id, locator
            FROM items WHERE item_id='item_knuckledusters'"""
        ).fetchone()
        self.assertEqual(item[0], 0)
        self.assertEqual(item[1], "game8_knuckledusters")
        self.assertTrue(item[2])
        panel_rows = self.connection.execute(
            """SELECT p.game_version, p.panel_rank, a.source_id, a.locator
            FROM lucky_panel_rewards r
            JOIN lucky_panel_pools p USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.item_id='item_knuckledusters'
            ORDER BY CAST(p.game_version AS INTEGER)"""
        ).fetchall()
        self.assertEqual(
            [(row[0], row[1]) for row in panel_rows],
            [("1", "3"), ("2", "2"), ("3", "1")],
        )
        self.assertTrue(all(row[2] == "rpgsite_lucky_panel" and row[3] for row in panel_rows))

        fixed_ids = (
            "acq_knuckledusters_pilgrims_perdition_past",
            "acq_iron_lance_grotta_sigillo_past",
            "acq_iron_lance_allblades_arena_past",
            "acq_yggdrasil_leaf_burnmont_past",
        )
        placeholders = ",".join("?" for _ in fixed_ids)
        rows = self.connection.execute(
            f"""SELECT acquisition_id, available_from_checkpoint_id,
                supply_type, finite_total, is_free, locator, verification_status
            FROM item_acquisition_paths WHERE acquisition_id IN ({placeholders})""",
            fixed_ids,
        ).fetchall()
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 and row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["locator"] for row in rows))
        by_id = {row["acquisition_id"]: row for row in rows}
        knuckles = by_id["acq_knuckledusters_pilgrims_perdition_past"]
        self.assertEqual(knuckles["verification_status"],
                         "direct_english_video_exact_container_platform_patch_unstated")
        self.assertIn("east/right closet", knuckles["locator"])
        self.assertEqual(by_id["acq_yggdrasil_leaf_burnmont_past"][
            "verification_status"], "two_source_route_exact_container_resolved")
        self.assertEqual(by_id["acq_iron_lance_grotta_sigillo_past"][
            "verification_status"], "source_checked_exact_container")
        self.assertEqual(by_id["acq_iron_lance_allblades_arena_past"][
            "verification_status"], "source_checked_exact_container")

    def test_tablet_registry_is_complete_and_resolves_achievement(self):
        totals = self.connection.execute(
            """SELECT COUNT(*), SUM(required_fragment_count) FROM stone_tablets"""
        ).fetchone()
        self.assertEqual(tuple(totals), (20, 71))
        ordinals = [
            row[0] for row in self.connection.execute(
                "SELECT source_ordinal FROM tablet_fragments ORDER BY source_ordinal"
            )
        ]
        self.assertEqual(ordinals, list(range(1, 72)))
        requirement = self.connection.execute(
            """SELECT target_type, target_key, required_count
            FROM achievement_requirements
            WHERE achievement_id = 'ach_no_stone_left_unturned'"""
        ).fetchone()
        self.assertEqual(
            tuple(requirement), ("stone_tablet_registry", "all", 20)
        )

    def test_final_gold_pedestal_unlock_has_two_independent_walkthroughs(self):
        rows = self.connection.execute(
            """SELECT c.value_json, c.locator, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='tablet:gold_pedestal_final_unlock'
              AND c.predicate='tablet_unlock_behavior'"""
        ).fetchall()
        self.assertEqual({row["publisher"] for row in rows},
                         {"Game8", "RPG Site"})
        self.assertTrue(all("Yet Another World" in row["value_json"]
                            for row in rows))
        self.assertTrue(all(row["locator"] for row in rows))

    def test_monster_and_vicious_registries_resolve_achievement_targets(self):
        monster_stats = self.connection.execute(
            """SELECT COUNT(*), MIN(source_ordinal), MAX(source_ordinal),
                SUM(rampaging), SUM(english_name IS NOT NULL) FROM monsters"""
        ).fetchone()
        self.assertEqual(tuple(monster_stats), (333, 1, 333, 35, 333))
        take_no_prisoners = self.connection.execute(
            """SELECT target_type, target_key, required_count
            FROM achievement_requirements
            WHERE achievement_id = 'ach_take_no_prisoners'"""
        ).fetchone()
        self.assertEqual(
            tuple(take_no_prisoners), ("monster_registry", "all", 333)
        )
        vanquisher = self.connection.execute(
            """SELECT target_type, target_key, required_count
            FROM achievement_requirements
            WHERE achievement_id = 'ach_vanquisher_of_the_vicious'"""
        ).fetchone()
        self.assertEqual(
            tuple(vanquisher), ("vicious_registry", "defeat_count", 10)
        )

    def test_early_monster_encounters_and_drops_are_checkpoint_scoped(self):
        counts = self.connection.execute(
            "SELECT (SELECT COUNT(*) FROM monster_encounters), "
            "(SELECT COUNT(*) FROM monster_drops)"
        ).fetchone()
        self.assertEqual(tuple(counts), (476, 227))
        early = self.connection.execute(
            """SELECT COUNT(DISTINCT monster_id), MIN(available_from_checkpoint_id),
                SUM(source_id NOT LIKE 'game8_monster_%')
            FROM monster_encounters"""
        ).fetchone()
        self.assertEqual(tuple(early), (333, "cp_001_prologue", 132))
        cactiball_drops = {
            row[0] for row in self.connection.execute(
                "SELECT item_name FROM monster_drops WHERE monster_id='monster_009'"
            )
        }
        self.assertEqual(cactiball_drops, {"Medicinal Herb", "Thorn Whip"})
        late_cleanup = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_blightcrawler',
                'game8_monster_mad_moai', 'game8_monster_terrorhawk')
              AND available_from_checkpoint_id='cp_026_elemental_cleanup_nottagen'"""
        ).fetchone()
        self.assertEqual(tuple(late_cleanup), (6, 3))
        late_hoarder_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_delusionist',
                'game8_monster_infernal_serpent',
                'game8_monster_hyperpyrexion', 'game8_monster_alarmour')
              AND available_from_checkpoint_id='cp_026_elemental_cleanup_nottagen'"""
        ).fetchone()
        self.assertEqual(tuple(late_hoarder_routes), (8, 4))
        cleanup_equipment_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_sculptrice',
                'game8_monster_fright_night', 'game8_monster_lethal_armour',
                'game8_monster_gigantes')
              AND available_from_checkpoint_id='cp_026_elemental_cleanup_nottagen'"""
        ).fetchone()
        self.assertEqual(tuple(cleanup_equipment_routes), (8, 4))
        late_area_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_merderer', 'game8_monster_seasaur',
                'game8_monster_mermaniac', 'game8_monster_croaked_king',
                'game8_monster_charmour', 'game8_monster_boss_troll',
                'game8_monster_drakulard', 'game8_monster_orc_king')"""
        ).fetchone()
        self.assertEqual(tuple(late_area_routes), (14, 8))
        final_cleanup_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_bone_baron',
                'game8_monster_manticore', 'game8_monster_juggular',
                'game8_monster_vis_mager', 'game8_monster_hyperanemon',
                'game8_monster_writhing_root', 'game8_monster_metal_heavy',
                'game8_monster_beastly_priest')"""
        ).fetchone()
        self.assertEqual(tuple(final_cleanup_routes), (13, 8))
        rampage_completion_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE encounter_id LIKE 'enc_rampaging_%_rampage_roads'
              AND location_text LIKE '%Road Round %'
              AND available_from_checkpoint_id='cp_031_testy_road_gold_gate'"""
        ).fetchone()
        self.assertEqual(tuple(rampage_completion_routes), (34, 34))
        completion_special_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE encounter_id IN (
                'enc_rampaging_goon_testy_road',
                'enc_colin_cocksure_bronze_cup',
                'enc_fair_weather_fred_bronze_cup',
                'enc_formidable_finn_bronze_cup',
                'enc_mossferatu_heavy_metal_hole_past',
                'enc_overtoad_slamphibians_heavy_metal_hole_past',
                'enc_toxic_toad_slamphibians_heavy_metal_hole_past',
                'enc_smothers_beacon_present'
            )"""
        ).fetchone()
        self.assertEqual(tuple(completion_special_routes), (8, 8))

        newly_routed = self.connection.execute(
            """SELECT COUNT(DISTINCT monster_id),
                SUM(verification_status LIKE 'cross_source_checked%'),
                SUM(verification_status LIKE 'single_independent_source%')
            FROM monster_encounters
            WHERE monster_id IN ('monster_040','monster_044','monster_058',
                'monster_076','monster_089','monster_137','monster_156',
                'monster_157','monster_158','monster_159','monster_160',
                'monster_161','monster_162','monster_163','monster_164',
                'monster_165','monster_209','monster_211','monster_251',
                'monster_275','monster_276')"""
        ).fetchone()
        self.assertEqual(tuple(newly_routed), (21, 11, 0))
        corroborating_claims = self.connection.execute(
            """SELECT COUNT(*) FROM claims
            WHERE claim_id LIKE 'claim_enc_%'
              AND verification_status LIKE 'cross_source_checked%'"""
        ).fetchone()[0]
        self.assertEqual(corroborating_claims, 20)

    def test_cp011_through_cp014_monsters_use_explicit_area_gates(self):
        checkpoints = dict(
            self.connection.execute(
                """SELECT available_from_checkpoint_id, COUNT(*)
                FROM monster_encounters
                WHERE available_from_checkpoint_id IN (
                    'cp_011_la_bravoure', 'cp_013_flying_carpet',
                    'cp_014_sir_mervyn'
                ) GROUP BY available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            checkpoints,
            {
                "cp_011_la_bravoure": 17,
                "cp_013_flying_carpet": 21,
                "cp_014_sir_mervyn": 4,
            },
        )
        self.assertEqual(
            self.connection.execute(
                """SELECT COUNT(*) FROM monster_encounters
                WHERE source_id='game8_monster_drag_racer'
                  AND location_text='Aeolus Vale Region'"""
            ).fetchone()[0],
            1,
        )

    def test_scarewell_fixed_route_and_ps5_reset_are_explicitly_scoped(self):
        encounter = self.connection.execute(
            """SELECT location_text, confidence, verification_status
            FROM monster_encounters
            WHERE encounter_id='enc_scarewell_hardlypool_region_past'"""
        ).fetchone()
        self.assertEqual(encounter["location_text"],
                         "Hardlypool Region, a little southwest of Spliton-on-Sea")
        self.assertEqual(encounter["confidence"], "verified")
        self.assertIn("cross_source_checked", encounter["verification_status"])
        route_claims = self.connection.execute(
            """SELECT DISTINCT s.publisher FROM claims c
            JOIN sources s USING(source_id)
            WHERE c.subject_key='monster:scarewell'
              AND c.predicate='fixed_encounter_route'"""
        ).fetchall()
        self.assertEqual(len(route_claims), 2)
        reset = self.connection.execute(
            """SELECT scope_json, verification_status FROM claims
            WHERE claim_id='claim_scarewell_town_reset_reddit_ps5'"""
        ).fetchone()
        self.assertEqual(json.loads(reset["scope_json"])["platform"], "PS5")
        self.assertIn("numeric_yield_excluded", reset["verification_status"])
        farm = self.connection.execute(
            """SELECT encounter_rate_text, verification_status FROM farming_spots
            WHERE farming_id='farm_strength_seed_scarewell'"""
        ).fetchone()
        self.assertIn("no cross-platform", farm["encounter_rate_text"])
        self.assertIn("numeric_rate_excluded", farm["verification_status"])
        advice = self.connection.execute(
            """SELECT applicability_json FROM checkpoint_advice
            WHERE advice_id='advice_cp013_scarewell_strength_seed'"""
        ).fetchone()
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(applicability["rate"], "unknown")
        self.assertEqual(len(applicability["evidence_claim_ids"]), 3)

    def test_cp015_through_cp019_monsters_keep_later_routes_later_gated(self):
        checkpoints = dict(
            self.connection.execute(
                """SELECT available_from_checkpoint_id, COUNT(*)
                FROM monster_encounters
                WHERE available_from_checkpoint_id IN (
                    'cp_015_greenthumb', 'cp_016_hubble', 'cp_019_aeolus'
                ) GROUP BY available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            checkpoints,
            {
                "cp_015_greenthumb": 5,
                "cp_016_hubble": 15,
                "cp_019_aeolus": 17,
            },
        )
        later_routes = dict(
            self.connection.execute(
                """SELECT location_text, available_from_checkpoint_id
                FROM monster_encounters
                WHERE location_text IN ('Buccanham Region', 'Coral Cave',
                    'Heavy Metal-Hole')
                GROUP BY location_text, available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            set(later_routes.values()),
            {"cp_020_buccanham", "cp_026_elemental_cleanup_nottagen"},
        )

    def test_cp020_through_cp025_monsters_use_explicit_area_gates(self):
        checkpoints = dict(
            self.connection.execute(
                """SELECT available_from_checkpoint_id, COUNT(*)
                FROM monster_encounters
                WHERE available_from_checkpoint_id IN (
                    'cp_020_buccanham', 'cp_021_malign_shrine',
                    'cp_023_fire_spirit', 'cp_025_wind_spirit'
                ) GROUP BY available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            checkpoints,
            {
                "cp_020_buccanham": 49,
                "cp_021_malign_shrine": 15,
                "cp_023_fire_spirit": 5,
                "cp_025_wind_spirit": 6,
            },
        )

    def test_monster_report_resolves_name_id_and_ordinal(self):
        by_name = load_monster_report(self.db_path, "Cactiball")
        by_id = load_monster_report(self.db_path, "monster_009")
        by_number = load_monster_report(self.db_path, "#9")
        self.assertEqual(by_name["monster"]["monster_id"], "monster_009")
        self.assertEqual(by_id["monster"], by_number["monster"])
        self.assertTrue(by_name["encounters"])
        self.assertEqual(len(by_name["drops"]), 2)
        output = io.StringIO()
        with redirect_stdout(output):
            print_monster_report(by_name)
        self.assertIn("#9 Cactiball", output.getvalue())
        self.assertIn("Find:", output.getvalue())
        self.assertIn("Drops:", output.getvalue())

    def test_checkpoint_monsters_hide_explicitly_completed_entries(self):
        state_path = Path(self.tempdir.name) / "monster-checkpoint.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["monster_entries"] = ["monster_009"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        remaining = load_checkpoint_monsters(
            self.db_path, state_path, "cp_003_ballymolloy"
        )
        self.assertNotIn("monster_009", [row["monster_id"] for row in remaining["monsters"]])
        complete = load_checkpoint_monsters(
            self.db_path, state_path, "cp_003_ballymolloy", include_completed=True
        )
        cactiball = next(row for row in complete["monsters"] if row["monster_id"] == "monster_009")
        self.assertTrue(cactiball["completed"])

    def test_monster_coverage_uses_only_explicit_player_state(self):
        state_path = Path(self.tempdir.name) / "monster-coverage.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["monster_entries"] = ["monster_009", "unknown_monster"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_monster_coverage(self.db_path, state_path)
        self.assertEqual(report["total"], 333)
        self.assertEqual(report["defeated"], 1)
        self.assertEqual(report["routed"], 333)
        self.assertEqual(report["drops"], 196)
        self.assertEqual(report["unknown_state_ids"], ["unknown_monster"])

    def test_player_progress_tracks_tablet_fragment_ids(self):
        state_path = Path(self.tempdir.name) / "tablet-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "tablet-found", ["tablet_fragment_001"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["tablet_fragments"], ["tablet_fragment_001"]
        )
        update_progress(
            state_path, self.db_path, "tablet-undo", ["tablet_fragment_001"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["tablet_fragments"], [])

    def test_player_progress_tracks_canonical_monster_hearts_reversibly(self):
        state_path = Path(self.tempdir.name) / "heart-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertNotIn("monster_hearts_owned", original["completion"])
        update_progress(state_path, self.db_path, "heart-obtained", ["heart_slime"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["monster_hearts_owned"], ["heart_slime"])
        update_progress(state_path, self.db_path, "heart-undo", ["heart_slime"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["monster_hearts_owned"], [])
        with self.assertRaisesRegex(ValueError, "Unknown Monster Heart"):
            update_progress(state_path, self.db_path, "heart-obtained", ["heart_fake"])

    def test_player_progress_tracks_dlc_entitlement_three_states_reversibly(self):
        state_path = Path(self.tempdir.name) / "dlc-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        scope = "Jam-Packed Swag Bag"
        update_progress(state_path, self.db_path, "dlc-entitlement", [scope, "owned"])
        self.assertEqual(json.loads(state_path.read_text())["dlc_entitlements"], {scope: True})
        update_progress(state_path, self.db_path, "dlc-entitlement", [scope, "not-owned"])
        self.assertEqual(json.loads(state_path.read_text())["dlc_entitlements"], {scope: False})
        update_progress(state_path, self.db_path, "dlc-entitlement", [scope, "unknown"])
        self.assertNotIn("dlc_entitlements", json.loads(state_path.read_text()))
        with self.assertRaisesRegex(ValueError, "Unknown DLC scope"):
            update_progress(state_path, self.db_path, "dlc-entitlement", ["Fake DLC", "owned"])

    def test_player_progress_tracks_party_wide_vocation_mastery(self):
        state_path = Path(self.tempdir.name) / "vocation-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "vocation-mastered", ["Hero", "vocation_warrior"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertIs(state["party"]["members"]["Hero"]["vocation_mastery"]["vocation_warrior"], True)
        update_progress(
            state_path, self.db_path, "vocation-undo", ["Hero", "vocation_warrior"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertNotIn(
            "vocation_warrior", state["party"]["members"]["Hero"]["vocation_mastery"]
        )

    def test_player_progress_tracks_explicit_level_and_current_vocations(self):
        state_path = Path(self.tempdir.name) / "party-details.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(state_path, self.db_path, "party-level", ["Hero", "17"])
        update_progress(state_path, self.db_path, "party-vocations",
                        ["Hero", "vocation_warrior", "vocation_priest"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        hero = state["party"]["members"]["Hero"]
        self.assertEqual((hero["level"], hero["primary_vocation"], hero["secondary_vocation"]),
                         (17, "vocation_warrior", "vocation_priest"))
        update_progress(state_path, self.db_path, "party-level", ["Hero", "unknown"])
        update_progress(state_path, self.db_path, "party-vocations",
                        ["Hero", "unknown", "unknown"])
        hero = json.loads(state_path.read_text(encoding="utf-8"))["party"]["members"]["Hero"]
        self.assertEqual((hero["level"], hero["primary_vocation"], hero["secondary_vocation"]),
                         (None, None, None))
        with self.assertRaisesRegex(ValueError, "positive integer"):
            update_progress(state_path, self.db_path, "party-level", ["Hero", "0"])
        with self.assertRaisesRegex(ValueError, "unavailable"):
            update_progress(state_path, self.db_path, "party-vocations",
                            ["Ruff", "vocation_fledgling_fisherman", "unknown"])

    def test_player_progress_tracks_monster_ordinals(self):
        state_path = Path(self.tempdir.name) / "monster-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(state_path, self.db_path, "monster-defeated", ["1", "Cactiball"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["monster_entries"], ["monster_001", "monster_009"]
        )
        update_progress(state_path, self.db_path, "monster-undo", ["#1", "monster_009"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["monster_entries"], [])
        with self.assertRaisesRegex(ValueError, "Ambiguous monster name"):
            update_progress(state_path, self.db_path, "monster-defeated", ["Orgodemir"])

        state_path = Path(self.tempdir.name) / "hoarder-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["items_obtained"] = [
            "item_pilchard_crackers", "unknown_item"
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_hoarder_report(self.db_path, state_path)
        self.assertEqual(report["obtained_count"], 1)
        self.assertEqual(report["unknown_state_ids"], ["unknown_item"])
        self.assertNotIn(
            "item_pilchard_crackers", {row["item_id"] for row in report["items"]}
        )

    def test_player_progress_records_and_reopens_hoarder_items(self):
        state_path = Path(self.tempdir.name) / "hoarder-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "item-obtained", ["item_pilchard_crackers"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["items_obtained"], ["item_pilchard_crackers"]
        )
        update_progress(
            state_path, self.db_path, "item-undo", ["item_pilchard_crackers"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["items_obtained"], [])

    def test_medal_078_conflict_resolves_to_screenshot_corroborated_route(self):
        row = self.connection.execute(
            """SELECT c.status, c.detection_method, c.resolution_claim_id,
                c.rationale
            FROM conflicts c
            WHERE c.claim_a_id = 'claim_medal_078_game8_floor'
              AND c.claim_b_id = 'claim_medal_078_rpgsite_floor'"""
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "resolved")
        self.assertEqual(row["detection_method"],
                         "manual_screenshot_route_adjudication")
        self.assertEqual(row["resolution_claim_id"],
                         "claim_medal_078_rpgsite_floor")
        self.assertIn("Level 3", row["rationale"])
        medal = self.connection.execute(
            """SELECT detail, source_id, verification_status
            FROM mini_medal_locations WHERE medal_number=78"""
        ).fetchone()
        self.assertEqual(medal["detail"],
                         "Exit south from 3F and open the chest on the outside balcony.")
        self.assertEqual(medal["source_id"], "rpgsite_walkthrough")
        self.assertIn("screenshot", medal["verification_status"])

    def test_phase_two_source_disagreements_are_visible(self):
        pairs = self.connection.execute(
            """SELECT claim_a_id, claim_b_id FROM conflicts
            WHERE claim_a_id LIKE 'claim_elevating_shoes_%'
               OR claim_a_id LIKE 'claim_cautery_sword_%'"""
        ).fetchall()
        self.assertEqual(len(pairs), 2)

        cautery = self.connection.execute(
            """SELECT status, resolution_claim_id, detection_method, rationale
            FROM conflicts WHERE claim_a_id LIKE 'claim_cautery_sword_%'
               OR claim_b_id LIKE 'claim_cautery_sword_%'"""
        ).fetchone()
        self.assertEqual(cautery["status"], "resolved")
        self.assertEqual(cautery["resolution_claim_id"],
                         "claim_cautery_sword_rpgsite_location")
        self.assertEqual(cautery["detection_method"],
                         "manual_direct_item_page_adjudication")
        self.assertIn("dedicated Cautery Sword acquisition page",
                      cautery["rationale"])

        elevating = self.connection.execute(
            """SELECT status, resolution_claim_id, detection_method, rationale
            FROM conflicts WHERE claim_a_id LIKE 'claim_elevating_shoes_%'
               OR claim_b_id LIKE 'claim_elevating_shoes_%'"""
        ).fetchone()
        self.assertEqual(elevating["status"], "resolved")
        self.assertEqual(elevating["resolution_claim_id"],
                         "claim_elevating_shoes_game8_routes")
        self.assertEqual(elevating["detection_method"],
                         "manual_direct_item_acquisition_adjudication")
        self.assertIn("Metal King Slime", elevating["rationale"])
        self.assertIn("rate", elevating["rationale"])

    def test_tempest_shield_locations_are_distinct_acquisition_routes(self):
        routes = self.connection.execute(
            """SELECT location_text, available_from_checkpoint_id, source_id
            FROM item_acquisition_paths
            WHERE item_id='item_tempest_shield' AND method='chest'
            ORDER BY available_from_checkpoint_id"""
        ).fetchall()
        self.assertEqual([tuple(row) for row in routes], [
            ("Sanctum of the Cirrus", "cp_019_aeolus", "game8_tempest_shield"),
            ("Ventus Tower 2F, by the north stairs", "cp_025_wind_spirit",
             "rpgsite_walkthrough"),
        ])
        conflict = self.connection.execute(
            """SELECT 1 FROM conflicts c JOIN claims a ON a.claim_id=c.claim_a_id
            WHERE a.subject_key='item:tempest_shield'
              AND a.predicate IN ('acquisition_location', 'precise_location_description')
              AND c.status='unresolved'"""
        ).fetchone()
        self.assertIsNone(conflict)
        predicates = self.connection.execute(
            """SELECT DISTINCT predicate FROM claims
            WHERE subject_key='item:tempest_shield'
              AND claim_id LIKE 'claim_tempest_shield_%location'"""
        ).fetchall()
        self.assertEqual([row[0] for row in predicates], ["acquisition_location"])

    def test_iron_shield_conflict_and_shell_shield_identity_are_resolved(self):
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id LIKE 'claim_iron_shield_%'
               OR claim_b_id LIKE 'claim_iron_shield_%'"""
        ).fetchone()
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["status"], "resolved")
        resolved = self.connection.execute(
            """SELECT resolution_claim_id, detection_method, rationale FROM conflicts
            WHERE claim_a_id LIKE 'claim_iron_shield_%'
               OR claim_b_id LIKE 'claim_iron_shield_%'"""
        ).fetchone()
        self.assertEqual(resolved["resolution_claim_id"],
                         "claim_iron_shield_game8_alltrades_price")
        self.assertEqual(resolved["detection_method"],
                         "manual_direct_location_shop_adjudication")
        self.assertIn("dedicated Alltrades Abbey map shop table", resolved["rationale"])
        scale_claim = self.connection.execute(
            """SELECT value_json FROM claims
            WHERE claim_id = 'claim_scale_shield_game8_lucky_panel_unspecified'"""
        ).fetchone()
        self.assertIsNotNone(scale_claim)
        self.assertEqual(json.loads(scale_claim["value_json"])["rank"], "unknown")
        typed_route = self.connection.execute(
            """SELECT p.*, r.pool_id, r.probability_text
            FROM item_acquisition_paths p
            JOIN lucky_panel_rewards r USING (acquisition_id)
            WHERE p.acquisition_id='acq_scale_shield_lucky_panel_v2_rank1'"""
        ).fetchone()
        self.assertIsNotNone(typed_route)
        self.assertEqual(typed_route["item_id"], "item_scale_shield")
        self.assertEqual(typed_route["time_period"], "Present")
        self.assertEqual(typed_route["pool_id"],
                         "lp_pilgrims_rest_v2_rank_1_standard")
        self.assertIsNone(typed_route["probability_text"])
        alias = self.connection.execute(
            """SELECT alias, verification_status FROM item_aliases
            WHERE alias_id='item_alias_shell_shield_rpgsite'"""
        ).fetchone()
        self.assertEqual(alias["alias"], "Shell Shield")
        self.assertIn("source_error", alias["verification_status"])
        publishers = self.connection.execute(
            """SELECT DISTINCT s.publisher FROM claims c
            JOIN sources s ON s.source_id=c.source_id
            WHERE c.subject_key='item:scale_shield'
              AND c.predicate='lucky_panel_rank_route'"""
        ).fetchall()
        self.assertEqual({row[0] for row in publishers}, {"GameWith", "hyperWiki"})

    def test_ice_shield_treasure_conflict_is_visible(self):
        conflicts = self.connection.execute(
            """SELECT status, resolution_claim_id, detection_method FROM conflicts
            WHERE claim_a_id LIKE 'claim_ice_shield_%'
               OR claim_b_id LIKE 'claim_ice_shield_%'"""
        ).fetchall()
        self.assertEqual(len(conflicts), 2)
        self.assertTrue(all(row["status"] == "resolved" for row in conflicts))
        self.assertEqual(
            {row["resolution_claim_id"] for row in conflicts},
            {"claim_ice_shield_rpgsite_past_chest",
             "claim_ice_shield_game8_hardlypool_map_chest"},
        )
        self.assertTrue(all(row["detection_method"] ==
                            "manual_direct_location_map_adjudication"
                            for row in conflicts))
        _, _, verdict = load_purchase_advice(
            self.db_path, "Ice Shield", "cp_013_flying_carpet"
        )
        self.assertNotIn("acquisition evidence conflict", verdict)

    def test_tempest_shield_multiple_routes_do_not_block_purchase_advice(self):
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id LIKE 'claim_tempest_shield_%'
               OR claim_b_id LIKE 'claim_tempest_shield_%'"""
        ).fetchone()
        self.assertIsNone(conflict)
        _, _, verdict = load_purchase_advice(
            self.db_path, "Tempest Shield", "cp_025_wind_spirit"
        )
        self.assertNotIn("acquisition evidence conflict", verdict)

    def test_acquisition_availability_separates_gates_from_route_metadata(self):
        descriptive = route_availability(
            "open", {"container": "east chest", "room": "north room"}, {})
        self.assertEqual(descriptive["availability_status"], "available_now")
        unknown_medals = route_availability(
            "open", {"mini_medals": 20}, {"completion": {}})
        self.assertEqual(unknown_medals["availability_status"],
                         "conditionally_available")
        self.assertEqual(unknown_medals["prerequisite_status"], "unknown")
        unmet_medals = route_availability(
            "open", {"mini_medals": 20},
            {"completion": {"mini_medal_count": 19}})
        self.assertEqual(unmet_medals["availability_status"], "unavailable")
        met_medals = route_availability(
            "open", {"mini_medals": 20},
            {"completion": {"mini_medal_count": 20}})
        self.assertEqual(met_medals["availability_status"], "available_now")
        key_gate = route_availability("open", {"key": "Magic Key"}, {})
        self.assertEqual(key_gate["availability_status"], "available_now")
        self.assertEqual(key_gate["prerequisite_status"], "not_applicable")
        self.assertEqual(key_gate["route_condition_keys"], ["key"])

    def test_purchase_advice_never_calls_unconfirmed_medal_route_free_now(self):
        _, routes, verdict = load_purchase_advice(
            self.db_path, "Magic Shield", "cp_009_alltrades")
        medal_route = next(row for row in routes
                           if row["acquisition_id"] ==
                           "acq_magic_shield_medal_reward_20")
        self.assertEqual(medal_route["timing_status"],
                         "checkpoint_open_prerequisite_unconfirmed")
        self.assertEqual(medal_route["availability_status"],
                         "conditionally_available")
        self.assertNotIn("verified free route available now", verdict)

    def test_conflict_detector_opens_stable_fact_conflict(self):
        path = Path(self.tempdir.name) / "conflict.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            values = (
                ("test_fact_a", '{"answer": 1}'),
                ("test_fact_b", '{"answer": 2}'),
            )
            for claim_id, value in values:
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'test:subject', 'version_count', ?, 'fact',
                        '{"game":"DQ7 Reimagined"}', 'game8_hub', 'test row',
                        'low', 'test_only', 'native')""",
                    (claim_id, value),
                )
            self.assertEqual(detect_conflicts(connection), 1)
            self.assertEqual(detect_conflicts(connection), 0)
            row = connection.execute(
                """SELECT claim_a_id, claim_b_id, status, detection_method
                FROM conflicts WHERE claim_a_id = 'test_fact_a'"""
            ).fetchone()
            self.assertEqual(tuple(row), (
                "test_fact_a", "test_fact_b", "unresolved", "automatic_exact_scope"
            ))
        finally:
            connection.close()

    def test_conflict_detector_ignores_recommendations(self):
        path = Path(self.tempdir.name) / "recommendations.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            for claim_id, value in (("rec_a", '"A"'), ("rec_b", '"B"')):
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'test:build', 'best', ?, 'recommendation',
                        '{}', 'game8_hub', 'test row', 'low', 'test_only', 'native')""",
                    (claim_id, value),
                )
            self.assertEqual(detect_conflicts(connection), 0)
        finally:
            connection.close()

    def test_conflict_detector_ignores_unregistered_predicate(self):
        path = Path(self.tempdir.name) / "unregistered-conflict.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            for claim_id, value in (("route_a", '"chest"'), ("route_b", '"drop"')):
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'item:test', 'obtained_from', ?, 'fact', '{}',
                        'game8_hub', 'test row', 'low', 'test_only', 'native')""",
                    (claim_id, value),
                )
            self.assertEqual(detect_conflicts(connection), 0)
        finally:
            connection.close()

    def test_conflict_report_returns_full_provenance(self):
        path = Path(self.tempdir.name) / "conflict-report.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            for claim_id, value, source_id in (
                ("report_a", "1", "game8_hub"),
                ("report_b", "2", "rpgsite_walkthrough"),
            ):
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'test:report', 'total_count', ?, 'fact', '{}',
                        ?, 'test locator', 'low', 'test_only', 'native')""",
                    (claim_id, value, source_id),
                )
            detect_conflicts(connection)
            connection.commit()
        finally:
            connection.close()
        rows = load_conflicts(path)
        row = next(item for item in rows if item["claim_a_id"] == "report_a")
        self.assertEqual(row["source_title_a"], "Dragon Quest 7 Reimagined Walkthrough & Guides Wiki")
        self.assertIn("rpgsite.net", row["source_url_b"])

    def test_vocation_relationships_are_valid(self):
        invalid = self.connection.execute(
            """SELECT r.relationship_id FROM relationships r
            LEFT JOIN entities s ON s.entity_id = r.subject_id
            LEFT JOIN entities o ON o.entity_id = r.object_id
            WHERE s.entity_id IS NULL OR o.entity_id IS NULL"""
        ).fetchall()
        self.assertEqual(invalid, [])

    def test_advanced_requirement_rules(self):
        rows = self.connection.execute(
            """SELECT v.name, vr.rule, vr.required_count, COUNT(*) AS candidates
            FROM vocation_requirements vr
            JOIN vocations vo ON vo.vocation_id = vr.vocation_id
            JOIN entities v ON v.entity_id = vo.vocation_id
            WHERE vo.tier = 'advanced'
            GROUP BY v.name, vr.group_id, vr.rule, vr.required_count
            ORDER BY v.name"""
        ).fetchall()
        actual = {row["name"]: (row["rule"], row["required_count"], row["candidates"]) for row in rows}
        self.assertEqual(actual["Champion"], ("all_of", 2, 2))
        self.assertEqual(actual["Druid"], ("any_n_of", 2, 3))
        self.assertEqual(actual["Hero"], ("any_n_of", 3, 7))

    def test_fts_smoke_query(self):
        rows = search(self.db_path, "alltrades vocation", limit=8)
        titles = {row["title"] for row in rows}
        self.assertIn("Alltrades Abbey power spike", titles)
        self.assertIn("Vocation prerequisite graph", titles)

    def test_fts_query_handles_empty_and_punctuation(self):
        self.assertEqual(search(self.db_path, "\"'!?", limit=8), [])
        rows = search(self.db_path, 'alltrades foo"bar', limit=8)
        self.assertTrue(rows)

    def test_search_prioritizes_structured_priority_identities_and_claims(self):
        shell = search(self.db_path, "Shell Shield", limit=4)
        self.assertEqual(shell[0]["title"], "Shell Shield → Scale Shield")
        slime = search(self.db_path, "Slime Earring", limit=4)
        self.assertTrue(any("Slime Earring" in row["title"] for row in slime))
        stella = search(self.db_path, "Stella Fan", limit=4)
        self.assertEqual(stella[0]["title"], "Stella Fan → Stellar Fan")
        orgodemir = search(self.db_path, "Orgodemir Magic Barrier", limit=8)
        self.assertTrue(any(row["domain"] == "claim" and
                            "orgodemir" in row["title"].casefold()
                            for row in orgodemir))
        self.assertTrue(all(row["source_url"] and row["locator"]
                            for row in (shell[0], stella[0])))

        repeatable_heart = search(self.db_path, "repeatable Monster Heart", limit=4)
        self.assertEqual(repeatable_heart[0]["domain"], "evidence gap")
        self.assertIn("No checked source proves a repeatable", repeatable_heart[0]["body"])
        self.assertTrue(repeatable_heart[0]["evidence"])
        self.assertTrue(all(row["locator"] for row in repeatable_heart[0]["evidence"]))

        panel_probability = search(self.db_path, "Lucky Panel probability", limit=4)
        self.assertEqual(panel_probability[0]["document_id"],
                         "evidence-gap:gap_lucky_panel_probabilities")
        self.assertEqual(panel_probability[0]["evidence"][0]["claim_id"],
                         "claim_lucky_panel_numeric_cells")

        gap_queries = {
            "Can I still get the Little Blue Button?": "gap_blue_button_cutoff",
            "What are Lucky Panel odds?": "gap_lucky_panel_probabilities",
            "How much EXP per hour farming?": "gap_reproducible_farm_rates",
            "best EXP farming rate": "gap_reproducible_farm_rates",
            "Can I farm Monster Hearts repeatedly?": "gap_repeatable_monster_hearts",
            "Can I equip two of the same accessory?": "gap_duplicate_equipment_stacking",
            "Do achievement counters carry over New Game?":
                "gap_achievement_counter_semantics",
        }
        for query, gap_id in gap_queries.items():
            with self.subTest(query=query):
                result = search(self.db_path, query, limit=4)[0]
                self.assertEqual(result["document_id"], f"evidence-gap:{gap_id}")
                self.assertIn("Needed:", result["body"])
                for evidence in result["evidence"]:
                    self.assertTrue(evidence["source_url"])
                    self.assertTrue(evidence["locator"])
                self.assertTrue(result["evidence"])

        ruby = search(self.db_path, "Ruby of Protection left drawer", limit=4)
        self.assertIn(ruby[0]["document_id"], {
            "claim:claim_ruby_protection_left_drawer_appmedia",
            "claim:claim_ruby_protection_left_drawer_altema",
        })
        self.assertTrue(ruby[0]["source_url"])
        self.assertTrue(ruby[0]["locator"])

    def test_search_does_not_create_missing_database(self):
        missing = Path(self.tempdir.name) / "missing.sqlite"
        with self.assertRaises(FileNotFoundError):
            search(missing, "alltrades")
        self.assertFalse(missing.exists())

    def test_phase_one_rows_have_precise_provenance(self):
        for table in ("mini_medal_locations", "checkpoint_obligations"):
            rows = self.connection.execute(
                f"""SELECT source_id, locator FROM {table}
                WHERE source_id IS NULL OR trim(locator) = ''"""
            ).fetchall()
            self.assertEqual(rows, [], table)

    def test_phase_two_rows_have_precise_provenance(self):
        for table in ("items", "item_acquisition_paths", "shops", "lucky_panel_pools"):
            rows = self.connection.execute(
                f"SELECT rowid FROM {table} WHERE source_id IS NULL OR trim(locator) = ''"
            ).fetchall()
            self.assertEqual(rows, [], table)

    def test_typed_acquisition_details_match_parent_method(self):
        bad_shop = self.connection.execute(
            """SELECT si.acquisition_id FROM shop_inventory si
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.method != 'shop'"""
        ).fetchall()
        bad_panel = self.connection.execute(
            """SELECT lr.acquisition_id FROM lucky_panel_rewards lr
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.method != 'lucky_panel'"""
        ).fetchall()
        self.assertEqual(bad_shop, [])
        self.assertEqual(bad_panel, [])
        missing_shop = self.connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            LEFT JOIN shop_inventory si USING(acquisition_id)
            WHERE a.method = 'shop' AND si.acquisition_id IS NULL"""
        ).fetchall()
        missing_panel = self.connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            LEFT JOIN lucky_panel_rewards lr USING(acquisition_id)
            WHERE a.method = 'lucky_panel' AND lr.acquisition_id IS NULL"""
        ).fetchall()
        self.assertEqual(missing_shop, [])
        self.assertEqual(missing_panel, [])

    def test_no_container_unspecified_residual_remains(self):
        rows = self.connection.execute(
            """SELECT method, COUNT(*) AS row_count
            FROM item_acquisition_paths
            WHERE verification_status LIKE '%container_unspecified%'
            GROUP BY method ORDER BY method"""
        ).fetchall()
        self.assertEqual(rows, [])
        status = (ROOT / "INGEST_STATUS.md").read_text(encoding="utf-8")
        handoff = (ROOT / "HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("no `container_unspecified` acquisition row remains", status)
        self.assertIn("No route retains the former `container_unspecified` status tag", handoff)
        self.assertIn("This does not mean\nevery finite route is individually exact", handoff)
        ruby_claims = self.connection.execute(
            """SELECT c.value_json, c.locator, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.claim_id IN (
                'claim_ruby_protection_left_drawer_appmedia',
                'claim_ruby_protection_left_drawer_altema'
            )"""
        ).fetchall()
        self.assertEqual({row["publisher"] for row in ruby_claims},
                         {"AppMedia", "Altema"})
        self.assertEqual(len({row["value_json"] for row in ruby_claims}), 1)
        self.assertTrue(all(row["locator"] for row in ruby_claims))

    def test_lordfenton_resolves_nine_residual_routes_without_ruby_inference(self):
        expected = {
            "acq_gold_bracer_temple_palace_past": "third chest result",
            "acq_silk_tuxedo_hubble_castle_past": "east/right",
            "acq_pretty_betsy_larca_region_present": "gold sparkle",
            "acq_super_pretty_betsy_yet_another_world": "beside pond",
            "acq_super_seed_of_life_yet_another_world": "narrow corridor",
            "acq_super_seed_of_strength_yet_another_world": "lava-surrounded",
            "acq_super_seed_of_deftness_yet_another_world": "southern dead end",
            "acq_super_seed_of_resilience_yet_another_world": "east/right chest",
            "acq_super_seed_of_therapeusis_yet_another_world": "water-bordered",
        }
        placeholders = ",".join("?" for _ in expected)
        rows = self.connection.execute(
            f"""SELECT acquisition_id, method, source_id, locator,
                verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN ({placeholders})""",
            tuple(expected),
        ).fetchall()
        self.assertEqual(len(rows), len(expected))
        for row in rows:
            self.assertTrue(row["source_id"].startswith("lordfenton_"))
            self.assertIn(expected[row["acquisition_id"]], row["locator"])
            self.assertNotIn("container_unspecified", row["verification_status"])
        claim_count = self.connection.execute(
            """SELECT COUNT(*) FROM claims
            WHERE claim_id LIKE '%_lordfenton'
              AND subject_key LIKE 'acquisition:%'"""
        ).fetchone()[0]
        self.assertGreaterEqual(claim_count, 9)

    def test_early_container_pass_resolves_fishnet_mermaid_and_ruby(self):
        fishnet = self.connection.execute(
            """SELECT method, prerequisite_json, locator, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_fishnet_stockings_allblades_arena'"""
        ).fetchone()
        self.assertEqual(fishnet["method"], "other")
        self.assertEqual(json.loads(fishnet["prerequisite_json"])["container"],
                         "east closet")
        self.assertIn("east closet", fishnet["locator"])
        self.assertNotIn("container_unspecified",
                         fishnet["verification_status"])
        mermaid = self.connection.execute(
            """SELECT method, source_id, prerequisite_json, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_mermaid_moon_wetlock_treasure'"""
        ).fetchone()
        self.assertEqual(mermaid["method"], "chest")
        self.assertEqual(mermaid["source_id"], "game8_walkthrough")
        self.assertIn("Hardlypool",
                      json.loads(mermaid["prerequisite_json"])["story"])
        self.assertNotIn("container_unspecified",
                         mermaid["verification_status"])
        ruby = self.connection.execute(
            """SELECT method, prerequisite_json, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_ruby_of_protection_faraday_castle'"""
        ).fetchone()
        details = json.loads(ruby["prerequisite_json"])
        self.assertEqual(details["container"], "left drawer")
        self.assertEqual(details["adjacent_container"],
                         "right drawer contains 200 gold")
        self.assertEqual(ruby["verification_status"],
                         "two_source_exact_container")

    def test_direct_heart_guide_resolves_two_exact_chests(self):
        rows = self.connection.execute(
            """SELECT acquisition_id, method, location_text, source_id, locator,
                verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_little_devil_heart_burnmount',
                'acq_healslime_heart_grotto_del_silgillo'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["method"], "chest")
            self.assertEqual(row["source_id"], "ngb_monster_hearts")
            self.assertIn("chest", row["locator"].casefold())
            self.assertEqual(row["verification_status"],
                             "source_checked_exact_chest")
        self.assertIn("exterior mountain ledge", rows[1]["location_text"])
        claim_count = self.connection.execute(
            """SELECT COUNT(*) FROM claims WHERE claim_id IN (
                'claim_little_devil_heart_exact_chest_ngb',
                'claim_healslime_heart_exact_chest_ngb')"""
        ).fetchone()[0]
        self.assertEqual(claim_count, 2)

    def test_direct_heart_guide_resolves_four_later_exact_routes(self):
        expected = {
            "acq_hypothermion_heart_malign_shrine": ("chest", "southeastern"),
            "acq_wight_watchman_heart_the_beacon": ("other", "gold item"),
            "acq_goodybag_heart_the_sea_dragon": ("chest", "Below Decks"),
            "acq_drakulard_heart_another_world": ("chest", "Ultimate Key"),
        }
        placeholders = ",".join("?" for _ in expected)
        rows = self.connection.execute(
            f"""SELECT acquisition_id, method, source_id, locator,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id IN ({placeholders})""",
            tuple(expected),
        ).fetchall()
        self.assertEqual(len(rows), 4)
        for row in rows:
            method, locator_fragment = expected[row["acquisition_id"]]
            self.assertEqual(row["method"], method)
            self.assertEqual(row["source_id"], "ngb_monster_hearts")
            self.assertIn(locator_fragment, row["locator"])
            self.assertNotIn("container_unspecified", row["verification_status"])
        claim_count = self.connection.execute(
            """SELECT COUNT(*) FROM claims WHERE claim_id IN (
                'claim_hypothermion_heart_exact_chest_ngb',
                'claim_wight_watchman_heart_exact_pickup_ngb',
                'claim_goodybag_heart_exact_chest_ngb',
                'claim_drakulard_heart_exact_chest_ngb')"""
        ).fetchone()[0]
        self.assertEqual(claim_count, 4)

    def test_hubble_princess_and_tuxedo_routes_are_exact(self):
        princess = self.connection.execute(
            """SELECT method, source_id, locator, prerequisite_json,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id='acq_princesss_robe_hubble_castle_past'"""
        ).fetchone()
        self.assertEqual(princess["method"], "chest")
        self.assertEqual(princess["source_id"], "ngb_magic_key_chests")
        self.assertIn("Chest #7", princess["locator"])
        self.assertEqual(json.loads(princess["prerequisite_json"])["key"],
                         "Magic Key")
        self.assertNotIn("container_unspecified",
                         princess["verification_status"])
        tuxedo = self.connection.execute(
            """SELECT method, source_id, prerequisite_json, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_silk_tuxedo_hubble_castle_past'"""
        ).fetchone()
        self.assertEqual(tuxedo["method"], "other")
        self.assertEqual(tuxedo["source_id"], "lordfenton_hubble_past_video")
        details = json.loads(tuxedo["prerequisite_json"])
        self.assertEqual(details["container"],
                         "east/right dresser of the adjacent north-wall pair")
        self.assertEqual(details["alternate_area_label"], "NW Tower 3F")
        self.assertNotIn("container_unspecified", tuxedo["verification_status"])

    def test_trophylink_resolves_five_exact_postgame_chests(self):
        expected = {
            "acq_day_off_dress_another_world": ("trophylink_day_off_dress_video", "center of three"),
            "acq_goddess_ring_yet_another_world": ("trophylink_goddess_ring_video", "western monster room"),
            "acq_ruinous_shield_yet_another_world": ("trophylink_ruinous_shield_video", "west/left"),
            "acq_super_seed_of_magic_yet_another_world": ("trophylink_gigant_armour_video", "west/left"),
            "acq_gigant_armour_yet_another_world": ("trophylink_gigant_armour_video", "east/right"),
        }
        rows = self.connection.execute(
            """SELECT acquisition_id, method, source_id, prerequisite_json,
                locator, verification_status FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_day_off_dress_another_world',
                'acq_goddess_ring_yet_another_world',
                'acq_ruinous_shield_yet_another_world',
                'acq_super_seed_of_magic_yet_another_world',
                'acq_gigant_armour_yet_another_world')"""
        ).fetchall()
        self.assertEqual(len(rows), 5)
        for row in rows:
            source_id, locator_fragment = expected[row["acquisition_id"]]
            self.assertEqual(row["method"], "chest")
            self.assertEqual(row["source_id"], source_id)
            self.assertIn(locator_fragment, row["locator"])
            self.assertIn("English result toast", row["locator"])
            self.assertNotIn("container_unspecified", row["verification_status"])
        claim_count = self.connection.execute(
            """SELECT COUNT(*) FROM claims WHERE claim_id IN (
                'claim_day_off_dress_exact_chest_trophylink',
                'claim_goddess_ring_exact_chest_trophylink',
                'claim_ruinous_shield_exact_chest_trophylink',
                'claim_super_seed_magic_exact_chest_trophylink',
                'claim_gigant_armour_exact_chest_trophylink')"""
        ).fetchone()[0]
        self.assertEqual(claim_count, 5)

        sources = self.connection.execute(
            """SELECT source_id, notes FROM sources
            WHERE source_id LIKE 'trophylink_%_video'"""
        ).fetchall()
        self.assertEqual(len(sources), 4)
        mismatch_sources = {row["source_id"]: row["notes"] for row in sources}
        for source_id in (
            "trophylink_ruinous_shield_video",
            "trophylink_gigant_armour_video",
            "trophylink_day_off_dress_video",
        ):
            self.assertIn("title says Past", mismatch_sources[source_id])
            self.assertIn("Present scope", mismatch_sources[source_id])

    def test_direct_postgame_evidence_resolves_three_exact_chests(self):
        rows = self.connection.execute(
            """SELECT acquisition_id, method, source_id, locator,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_sun_crown_another_world',
                'acq_super_seed_of_agility_yet_another_world',
                'acq_super_seed_of_sorcery_yet_another_world')"""
        ).fetchall()
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["method"], "chest")
            self.assertNotIn("container_unspecified",
                             row["verification_status"])
        by_id = {row["acquisition_id"]: row for row in rows}
        self.assertEqual(
            by_id["acq_sun_crown_another_world"]["source_id"],
            "codenamegaming_another_world_video")
        self.assertIn("west/left", by_id[
            "acq_sun_crown_another_world"]["locator"])
        for acquisition_id in (
            "acq_super_seed_of_agility_yet_another_world",
            "acq_super_seed_of_sorcery_yet_another_world",
        ):
            self.assertEqual(by_id[acquisition_id]["source_id"],
                             "neoseeker_yet_another_world")
            self.assertIn("Game8", by_id[acquisition_id]["locator"])
        claim_count = self.connection.execute(
            """SELECT COUNT(*) FROM claims WHERE claim_id IN (
                'claim_sun_crown_exact_chest_codenamegaming',
                'claim_super_seed_agility_exact_location_neoseeker',
                'claim_super_seed_agility_chest_class_game8',
                'claim_super_seed_sorcery_exact_location_neoseeker',
                'claim_super_seed_sorcery_chest_class_game8')"""
        ).fetchone()[0]
        self.assertEqual(claim_count, 5)

    def test_game8_postgame_resolves_great_helm_exact_chest(self):
        row = self.connection.execute(
            """SELECT method, location_text, source_id, locator,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id='acq_great_helm_another_world'"""
        ).fetchone()
        self.assertEqual(row["method"], "chest")
        self.assertEqual(row["location_text"],
                         "Another World 4F northern side")
        self.assertEqual(row["source_id"], "game8_postgame")
        self.assertIn("north chest contains Great Helm", row["locator"])
        self.assertEqual(row["verification_status"],
                         "source_checked_exact_chest")
        claim = self.connection.execute(
            """SELECT locator FROM claims
            WHERE claim_id='claim_great_helm_another_world_4f_north_chest_game8'"""
        ).fetchone()
        self.assertIsNotNone(claim)
        self.assertIn("left stairs from 3F", claim["locator"])

    def test_previously_unknown_shop_prices_are_typed_and_sourced(self):
        rows = self.connection.execute(
            """SELECT a.acquisition_id, a.method, a.source_id, si.price
            FROM item_acquisition_paths a
            JOIN shop_inventory si USING(acquisition_id)
            WHERE a.acquisition_id IN (
                'acq_dragon_robe_shop_rucker_castle_past',
                'acq_enchanted_armour_shop_rucker_castle_past',
                'acq_pilchard_pie_shop_pilchard'
            ) ORDER BY a.acquisition_id"""
        ).fetchall()
        self.assertEqual([tuple(row) for row in rows], [
            ('acq_dragon_robe_shop_rucker_castle_past', 'shop',
             'game8_dragon_robe', 19000),
            ('acq_enchanted_armour_shop_rucker_castle_past', 'shop',
             'game8_enchanted_armour', 21000),
            ('acq_pilchard_pie_shop_pilchard', 'shop',
             'game8_pilchard_bay_map', 10),
        ])

    def test_walkthrough_refines_finite_routes_without_erasing_pair_unknowns(self):
        exact_ids = {
            'acq_leather_hat_pilchard_bay_present',
            'acq_leather_hat_estard_present',
            'acq_pointy_hat_rainbow_mines_past',
            'acq_hardwood_headwear_ballymolloy_present',
            'acq_hairband_treasure_larca_past',
            'acq_rabbit_ears_treasure_larca_present',
            'acq_divine_dagger_burnmont_past',
            'acq_iron_lance_grotta_sigillo_past',
            'acq_scale_armour_frobisher_past',
            'acq_hardwood_headwear_faraday_castle_past',
            'acq_edged_boomerang_faraday_castle_past',
            'acq_noble_garb_institute_past',
            'acq_prayer_ring_tunnel_to_abbey_past',
            'acq_iron_lance_allblades_arena_past',
            'acq_silk_robe_bandits_base_present',
            'acq_ogre_shield_treasure_mount_gora_past',
            'acq_garter_greenthumb_region_present',
            'acq_lucida_shard_alltrades_past',
        }
        rows = self.connection.execute(
            f"""SELECT acquisition_id, source_id, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN ({','.join('?' for _ in exact_ids)})""",
            tuple(sorted(exact_ids)),
        ).fetchall()
        self.assertEqual({row['acquisition_id'] for row in rows}, exact_ids)
        self.assertTrue(all(row['source_id'] == 'rpgsite_walkthrough' for row in rows))
        self.assertTrue(all(row['verification_status'] == 'source_checked_exact_container'
                            for row in rows))

        residual = self.connection.execute(
            """SELECT COUNT(*) FROM item_acquisition_paths
            WHERE supply_type='finite' AND verification_status LIKE '%unknown%'"""
        ).fetchone()[0]
        self.assertEqual(residual, 0)
        strength_ring = self.connection.execute(
            """SELECT source_id, route_label, prerequisite_json, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_strength_ring_faraday_castle_past'"""
        ).fetchone()
        self.assertEqual(strength_ring["source_id"],
                         "hyunasae_faraday_castle_video")
        self.assertIn("lower drawer", strength_ring["route_label"])
        self.assertIn("lower/southern drawer",
                      json.loads(strength_ring["prerequisite_json"])["container"])
        self.assertEqual(strength_ring["verification_status"],
                         "direct_video_exact_container_two_source_route")
        handoff = (ROOT / "HANDOFF.md").read_text(encoding="utf-8")
        status = (ROOT / "INGEST_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("No route retains the former `container_unspecified` status tag", handoff)
        self.assertIn("no `container_unspecified` acquisition row remains",
                      status)
        self.assertIn("browser's six-item", status)
        corroborating = self.connection.execute(
            """SELECT c.subject_key, c.value_json, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.predicate='container_group_description'
              AND c.claim_id IN (
                'claim_strength_ring_faraday_drawer_pair_neoseeker',
                'claim_knuckledusters_strom_dresser_pair_neoseeker',
                'claim_silk_robe_temple_dresser_pair_neoseeker',
                'claim_dragon_shield_treasure_house_group_neoseeker',
                'claim_pirates_hat_buccanham_dresser_pair_neoseeker',
                'claim_steel_helmet_rucker_chest_pair_neoseeker'
              ) ORDER BY c.subject_key"""
        ).fetchall()
        self.assertEqual(len(corroborating), 6)
        self.assertTrue(all(row["publisher"] == "Neoseeker"
                            for row in corroborating))
        self.assertTrue(all(json.loads(row["value_json"])["individual_member"] ==
                            "unknown" for row in corroborating))

    def test_pirates_hat_period_conflict_is_resolved_but_visible(self):
        rows = self.connection.execute(
            """SELECT c.status, a.value_json AS value_a, b.value_json AS value_b
            FROM conflicts c
            JOIN claims a ON a.claim_id=c.claim_a_id
            JOIN claims b ON b.claim_id=c.claim_b_id
            WHERE a.subject_key='item:pirates_hat_buccanham_palace'"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['status'] == 'resolved' for row in rows))
        self.assertTrue(all({
            json.loads(row['value_a'])['time_period'],
            json.loads(row['value_b'])['time_period'],
        } == {'Past', 'Present'} for row in rows))

    def test_fishnet_stockings_period_conflict_is_resolved_but_visible(self):
        rows = self.connection.execute(
            """SELECT c.status, a.value_json AS value_a, b.value_json AS value_b
            FROM conflicts c
            JOIN claims a ON a.claim_id=c.claim_a_id
            JOIN claims b ON b.claim_id=c.claim_b_id
            WHERE a.subject_key='item:fishnet_stockings_frobisher'"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['status'] == 'resolved' for row in rows))
        self.assertTrue(all({
            json.loads(row['value_a'])['time_period'],
            json.loads(row['value_b'])['time_period'],
        } == {'Past', 'Present'} for row in rows))

    def test_metal_medal_and_cyclops_power_cards_have_narrow_atomic_evidence(self):
        advice_ids = {
            'advice_cp008_roamer_metal_slime_grind',
            'advice_cp013_highendreigh_metal_grind',
            'advice_cp018_cyclops_heart',
            'advice_cp020_sages_stone_65',
            'advice_cp024_sacreder_armour_80',
            'advice_cp032_metal_king_sword_100',
        }
        rows = self.connection.execute(
            f"""SELECT advice_id, applicability_json, verification_status
            FROM checkpoint_advice
            WHERE advice_id IN ({','.join('?' for _ in advice_ids)})""",
            tuple(sorted(advice_ids)),
        ).fetchall()
        self.assertEqual({row['advice_id'] for row in rows}, advice_ids)
        for row in rows:
            applicability = json.loads(row['applicability_json'])
            claim_ids = applicability['evidence_claim_ids']
            publishers = self.connection.execute(
                f"""SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.claim_id IN ({','.join('?' for _ in claim_ids)})""",
                tuple(claim_ids),
            ).fetchall()
            self.assertGreaterEqual(len(publishers), 2, row['advice_id'])
            self.assertIn('two_source_verified', row['verification_status'])

        by_id = {row['advice_id']: json.loads(row['applicability_json'])
                 for row in rows}
        for advice_id in ('advice_cp008_roamer_metal_slime_grind',
                          'advice_cp013_highendreigh_metal_grind'):
            self.assertEqual(by_id[advice_id]['rate'], 'unknown')
            self.assertIn('ceiling', by_id[advice_id])
        highendreigh = by_id['advice_cp013_highendreigh_metal_grind']
        self.assertIn("Ruff's Whistle", highendreigh['single_source_extras']['game8'])
        self.assertNotIn('repeatable',
                         by_id['advice_cp018_cyclops_heart'])

    def test_late_fixed_gear_cards_preserve_verified_subsets(self):
        advice_ids = {
            'advice_cp021_malign_fixed_gear',
            'advice_cp022_ultimate_key_gear',
            'advice_cp023_fire_route_gear',
        }
        rows = self.connection.execute(
            f"""SELECT advice_id, applicability_json, verification_status
            FROM checkpoint_advice
            WHERE advice_id IN ({','.join('?' for _ in advice_ids)})""",
            tuple(sorted(advice_ids)),
        ).fetchall()
        self.assertEqual({row['advice_id'] for row in rows}, advice_ids)
        by_id = {row['advice_id']: (json.loads(row['applicability_json']),
                                    row['verification_status'])
                 for row in rows}
        for advice_id, (applicability, status) in by_id.items():
            claim_ids = applicability['evidence_claim_ids']
            publishers = self.connection.execute(
                f"""SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.claim_id IN ({','.join('?' for _ in claim_ids)})""",
                tuple(claim_ids),
            ).fetchall()
            self.assertGreaterEqual(len(publishers), 2, advice_id)
            self.assertIn('two_source_verified', status)
        self.assertIn('teleportal', by_id[
            'advice_cp022_ultimate_key_gear'][0]['single_source_extra'][
                'rpgsite'].lower())
        fire = by_id['advice_cp023_fire_route_gear'][0]
        self.assertEqual(set(fire['verified_core']), {'Magma Staff'})
        self.assertEqual(set(fire['single_source_extra']), {'Sacred Armour'})

    def test_time_being_and_lourgh_keep_shared_tactics_and_scope_limits(self):
        rows = self.connection.execute(
            """SELECT advice_id, applicability_json, verification_status
            FROM checkpoint_advice
            WHERE advice_id IN ('advice_cp021_time_being',
                                'advice_cp027_lourgh_disorder')
            ORDER BY advice_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_id = {row['advice_id']: (json.loads(row['applicability_json']),
                                    row['verification_status'])
                 for row in rows}
        for advice_id, (applicability, status) in by_id.items():
            claim_ids = applicability['evidence_claim_ids']
            publishers = self.connection.execute(
                f"""SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.claim_id IN ({','.join('?' for _ in claim_ids)})""",
                tuple(claim_ids),
            ).fetchall()
            self.assertGreaterEqual(len(publishers), 2, advice_id)
            self.assertIn('two_source_verified', status)

        time_being = by_id['advice_cp021_time_being'][0]
        self.assertIn('multi-target healer',
                      time_being['single_source_extras']['game8'])
        self.assertNotIn('healing', time_being['verified_core'])

        lourgh = by_id['advice_cp027_lourgh_disorder'][0]
        self.assertEqual(lourgh['time_period'], 'Past')
        conflict_claims = {
            'claim_lourgh_location_game8_present',
            'claim_lourgh_location_eliteguias_past',
        }
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id IN (?, ?) AND claim_b_id IN (?, ?)""",
            tuple(sorted(conflict_claims)) * 2,
        ).fetchone()
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict['status'], 'resolved')
        self.assertIn('Game8 isolated boss page', lourgh['losing_source_claim'])

    def test_new_power_cores_have_two_publishers_and_keep_extras_scoped(self):
        advice_ids = {
            'advice_cp002_tribulators',
            'advice_cp011_la_bravoure_metal_king_grind',
            'advice_cp024_luminary_setup',
            'advice_cp025_monster_wrangler_summons',
            'advice_cp028_druid_sustained_summon',
            'advice_cp021_orgodemir_first',
        }
        rows = self.connection.execute(
            f"""SELECT advice_id, applicability_json, verification_status
            FROM checkpoint_advice
            WHERE advice_id IN ({','.join('?' for _ in advice_ids)})""",
            tuple(sorted(advice_ids)),
        ).fetchall()
        self.assertEqual({row['advice_id'] for row in rows}, advice_ids)
        for row in rows:
            applicability = json.loads(row['applicability_json'])
            claim_ids = applicability['evidence_claim_ids']
            publishers = self.connection.execute(
                f"""SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.claim_id IN ({','.join('?' for _ in claim_ids)})""",
                tuple(claim_ids),
            ).fetchall()
            self.assertGreaterEqual(len(publishers), 2, row['advice_id'])

        orgodemir = next(row for row in rows
                         if row['advice_id'] == 'advice_cp021_orgodemir_first')
        applicability = json.loads(orgodemir['applicability_json'])
        self.assertEqual(applicability['verified_core']['phase_2'],
                         'Use Insulatle to mitigate breath damage')
        self.assertEqual(applicability['losing_source_disagreement']['game8'],
                         'Magic Barrier in phase two')
        self.assertIn('phase_two_insulatle_three_source_verified',
                      orgodemir['verification_status'])
        phase_two = self.connection.execute(
            """SELECT c.claim_id, c.value_json, c.verification_status,
                s.publisher FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='boss:orgodemir_first'
              AND c.predicate='phase_two_breath_mitigation_recommendation'
            ORDER BY c.claim_id"""
        ).fetchall()
        self.assertEqual(len(phase_two), 4)
        self.assertEqual(len({row['publisher'] for row in phase_two
                              if json.loads(row['value_json']) == 'Insulatle'}), 3)
        losing = next(row for row in phase_two
                      if json.loads(row['value_json']) == 'Magic Barrier')
        self.assertIn('losing', losing['verification_status'])

    def test_route_level_supply_does_not_create_item_exclusivity(self):
        rows = self.connection.execute(
            """SELECT method, supply_type FROM item_acquisition_paths
            WHERE item_id = 'item_cottontail_costume'
            ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual([tuple(row) for row in rows], [
            ("lucky_panel", "renewable"), ("lucky_panel", "renewable")
        ])

    def test_lucky_panel_treasure_chest_matrices_are_version_scoped(self):
        pools = dict(self.connection.execute(
            """SELECT game_version, COUNT(lr.acquisition_id)
            FROM lucky_panel_pools lp JOIN lucky_panel_rewards lr USING(pool_id)
            WHERE chest_tier = 'treasure_chest' AND game_version IN ('2', '3')
            GROUP BY game_version"""
        ).fetchall())
        self.assertEqual(pools, {"2": 3, "3": 11})
        invented_values = self.connection.execute(
            """SELECT COUNT(*) FROM lucky_panel_rewards lr
            JOIN lucky_panel_pools lp USING(pool_id)
            WHERE lp.chest_tier = 'treasure_chest'
              AND lp.game_version IN ('2', '3')
              AND (lr.slot_count IS NOT NULL OR lr.probability_text IS NOT NULL)"""
        ).fetchone()[0]
        self.assertEqual(invented_values, 0)

    def test_lucky_panel_version_3_rank_1_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_1_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 25)
        self.assertIn("Chain Whip", {row["name"] for row in rows})
        self.assertIn("Stellar Fan", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 3" in row["locator"] and "Rank 1" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_3_rank_2_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.verification_status,
                lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_2_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 36)
        self.assertIn("Assassin's Dagger", {row["name"] for row in rows})
        self.assertIn("Pillager's Helmet", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 3" in row["locator"] and "Rank 2" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_3_rank_3_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_3_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 31)
        self.assertIn("Princess's Robe", {row["name"] for row in rows})
        self.assertIn("Zombiesbane", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 3" in row["locator"] and "Rank 3" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_3_rank_4_preserves_exclusivity_qualifiers(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.prerequisite_json,
                lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_4_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 21)
        by_name = {row["name"]: row for row in rows}
        for name in ("Fire Blade", "Metal Goomerang", "Thinking Cap"):
            self.assertIn("Lucky Panel exclusive", by_name[name]["locator"])
            self.assertEqual(
                json.loads(by_name[name]["prerequisite_json"])["source_qualifier"],
                "Lucky Panel exclusive",
            )
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_fire_blade_exclusive_label_loses_to_exact_finite_route(self):
        route = self.connection.execute(
            """SELECT method, location_text, available_from_checkpoint_id,
                prerequisite_json, source_id, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_fire_blade_burnmount_present_ultimate_key'"""
        ).fetchone()
        self.assertEqual(route["method"], "chest")
        self.assertIn("Level 5", route["location_text"])
        self.assertEqual(route["available_from_checkpoint_id"],
                         "cp_023_fire_spirit")
        self.assertEqual(json.loads(route["prerequisite_json"])["key"],
                         "Ultimate Key")
        self.assertIn("two_independent", route["verification_status"])
        conflicts = self.connection.execute(
            """SELECT status, rationale FROM conflicts
            WHERE claim_a_id='claim_fire_blade_lucky_panel_exclusive_rpgsite'
               OR claim_b_id='claim_fire_blade_lucky_panel_exclusive_rpgsite'"""
        ).fetchall()
        self.assertEqual(len(conflicts), 2)
        self.assertTrue(all(row["status"] == "resolved" for row in conflicts))
        self.assertTrue(all("Lucky Panel route remains valid" in row["rationale"]
                            for row in conflicts))

    def test_elemental_vault_rewards_have_exact_two_source_interactions(self):
        expected = {
            "acq_okeanos_sword_cathedral_blight": "Water Amulet",
            "acq_pyros_helm_cathedral_blight": "Fire Amulet",
            "acq_gaia_armour_cathedral_blight": "Earth Amulet",
        }
        for acquisition_id, amulet in expected.items():
            route = self.connection.execute(
                """SELECT route_label, location_text, prerequisite_json,
                    verification_status FROM item_acquisition_paths
                WHERE acquisition_id=?""", (acquisition_id,)
            ).fetchone()
            self.assertIn("pedestal reward", route["route_label"])
            self.assertIn("God's Treasure Vault", route["location_text"])
            self.assertIn(amulet,
                          json.loads(route["prerequisite_json"])["interaction"])
            self.assertIn("two_independent", route["verification_status"])
            publishers = self.connection.execute(
                """SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.subject_key=?
                  AND c.predicate='precise_acquisition_interaction'""",
                (f"acquisition:{acquisition_id}",),
            ).fetchall()
            self.assertEqual({row["publisher"] for row in publishers},
                             {"Game8 Japan", "Neoseeker"})

    def test_cathedral_gear_has_exact_two_source_pickups(self):
        expected = {
            "acq_helas_armour_chest_cathedral_blight":
                (("chest", "3F", "east"), {"RPG Site", "Gamers-High"}),
            "acq_orichalcum_fangs_cathedral_blight":
                (("chest", "4F", "north"), {"RPG Site", "Gamers-High"}),
            "acq_sword_of_ruin_cathedral_blight":
                (("other", "1F", "throne", "sparkle"),
                 {"RPG Site", "Gamers-High"}),
            "acq_headsmans_axe_cathedral_blight":
                (("chest", "B2", "left-hand door", "small room"),
                 {"Gamers-High", "Neoseeker"}),
        }
        for acquisition_id, (fragments, expected_publishers) in expected.items():
            route = self.connection.execute(
                """SELECT method, route_label, location_text, prerequisite_json,
                    verification_status FROM item_acquisition_paths
                WHERE acquisition_id=?""", (acquisition_id,)
            ).fetchone()
            combined = " ".join((route["method"], route["route_label"],
                                 route["location_text"], route["prerequisite_json"]))
            self.assertTrue(all(fragment in combined for fragment in fragments))
            self.assertIn("two_independent", route["verification_status"])
            publishers = self.connection.execute(
                """SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.subject_key=? AND c.predicate='precise_location_description'""",
                (f"acquisition:{acquisition_id}",),
            ).fetchall()
            self.assertEqual({row["publisher"] for row in publishers},
                             expected_publishers)

    def test_hidden_pyramid_power_items_have_exact_two_source_chests(self):
        expected = {
            "acq_double_edged_sword_hidden_pyramid_present":
                ("B1", "northwest"),
            "acq_skeleton_swordsman_heart_hidden_pyramid":
                ("B3", "south"),
            "acq_divine_bustier_chest_hidden_pyramid_present":
                ("B4", "south"),
        }
        for acquisition_id, fragments in expected.items():
            route = self.connection.execute(
                """SELECT route_label, location_text, prerequisite_json,
                    verification_status FROM item_acquisition_paths
                WHERE acquisition_id=?""", (acquisition_id,)
            ).fetchone()
            combined = " ".join((route["route_label"], route["location_text"],
                                 route["prerequisite_json"]))
            self.assertTrue(all(fragment in combined for fragment in fragments))
            self.assertIn("two_independent", route["verification_status"])
            publishers = self.connection.execute(
                """SELECT DISTINCT s.publisher FROM claims c
                JOIN sources s USING(source_id)
                WHERE c.subject_key=? AND c.predicate='precise_location_description'""",
                (f"acquisition:{acquisition_id}",),
            ).fetchall()
            self.assertEqual({row["publisher"] for row in publishers},
                             {"Gamers-High", "AppMedia"})

    def test_rippled_rapier_has_exact_two_source_story_gated_chest(self):
        acquisition_id = "acq_rippled_rapier_wetlock_present"
        route = self.connection.execute(
            """SELECT method, route_label, location_text, prerequisite_json,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id=?""", (acquisition_id,)
        ).fetchone()
        combined = " ".join((route["route_label"], route["location_text"],
                             route["prerequisite_json"]))
        self.assertEqual(route["method"], "chest")
        self.assertIn("underground storeroom", combined)
        self.assertIn("Red Fragment", combined)
        self.assertIn("Highendreigh Tower", combined)
        self.assertIn("two_independent", route["verification_status"])
        publishers = self.connection.execute(
            """SELECT DISTINCT s.publisher FROM claims c
            JOIN sources s USING(source_id)
            WHERE c.subject_key=? AND c.predicate='precise_location_description'""",
            (f"acquisition:{acquisition_id}",),
        ).fetchall()
        self.assertEqual({row["publisher"] for row in publishers},
                         {"Gamers-High", "AppMedia"})

    def test_demon_spear_corrects_inferred_chest_to_exact_gold_spot(self):
        acquisition_id = "acq_demon_spear_nottagen_cavern_past"
        route = self.connection.execute(
            """SELECT method, route_label, location_text, prerequisite_json,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id=?""", (acquisition_id,)
        ).fetchone()
        combined = " ".join((route["route_label"], route["location_text"],
                             route["prerequisite_json"])).lower()
        self.assertEqual(route["method"], "other")
        for fragment in ("b1", "screen-2", "back-left", "sparkle", "east-side"):
            self.assertIn(fragment, combined)
        self.assertIn("three_independent", route["verification_status"])
        publishers = self.connection.execute(
            """SELECT DISTINCT s.publisher FROM claims c
            JOIN sources s USING(source_id)
            WHERE c.subject_key=? AND c.predicate='precise_location_description'""",
            (f"acquisition:{acquisition_id}",),
        ).fetchall()
        self.assertEqual({row["publisher"] for row in publishers},
                         {"RPG Site", "Game8 Japan", "Neoseeker"})

    def test_falcon_knife_earrings_have_exact_isolated_falls_hollow_chest(self):
        acquisition_id = "acq_falcon_knife_earrings_falls_hollow"
        route = self.connection.execute(
            """SELECT method, route_label, location_text, prerequisite_json,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id=?""", (acquisition_id,)
        ).fetchone()
        combined = " ".join((route["route_label"], route["location_text"],
                             route["prerequisite_json"])).lower()
        self.assertEqual(route["method"], "chest")
        for fragment in ("isolated", "1f", "west", "b1", "staircase"):
            self.assertIn(fragment, combined)
        self.assertIn("two_independent", route["verification_status"])
        publishers = self.connection.execute(
            """SELECT DISTINCT s.publisher FROM claims c
            JOIN sources s USING(source_id)
            WHERE c.subject_key=? AND c.predicate='precise_location_description'""",
            (f"acquisition:{acquisition_id}",),
        ).fetchall()
        self.assertEqual({row["publisher"] for row in publishers},
                         {"RPG Site", "Neoseeker"})

    def test_heavens_talon_is_post_xenlon_orange_sparkle(self):
        acquisition_id = "acq_heavens_talon_yet_another_world"
        route = self.connection.execute(
            """SELECT method, route_label, location_text, prerequisite_json,
                verification_status FROM item_acquisition_paths
            WHERE acquisition_id=?""", (acquisition_id,)
        ).fetchone()
        combined = " ".join((route["route_label"], route["location_text"],
                             route["prerequisite_json"])).lower()
        self.assertEqual(route["method"], "other")
        for fragment in ("xenlon", "church", "orange sparkle", "where xenlon stood"):
            self.assertIn(fragment, combined)
        self.assertIn("two_independent", route["verification_status"])
        publishers = self.connection.execute(
            """SELECT DISTINCT s.publisher FROM claims c
            JOIN sources s USING(source_id)
            WHERE c.subject_key=? AND c.predicate='precise_location_description'""",
            (f"acquisition:{acquisition_id}",),
        ).fetchall()
        self.assertEqual({row["publisher"] for row in publishers},
                         {"Game8", "Neoseeker"})

    def test_repeatable_heart_gap_preserves_direct_negative_boundaries(self):
        rows = self.connection.execute(
            """SELECT c.claim_id, c.value_json, c.locator, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.claim_id IN (?,?,?) ORDER BY c.claim_id""",
            ("claim_numen_heart_initial_only_gamewith",
             "claim_arena_rewards_one_time_gamershigh",
             "claim_strong_monsters_finite_appmedia"),
        ).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["publisher"] for row in rows},
                         {"GameWith", "Gamers-High", "AppMedia"})
        combined = " ".join(row["value_json"] + " " + row["locator"]
                            for row in rows).lower()
        for fragment in ("numen heart", "subsequent", "one time", "disappear"):
            self.assertIn(fragment, combined)

    def test_lucky_panel_version_2_rank_1_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v2_rank_1_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 32)
        self.assertIn("Scale Shield", {row["name"] for row in rows})
        self.assertIn("Wizard's Staff", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 2" in row["locator"] and "Rank 1" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_010_alltrades_present"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_2_rank_2_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v2_rank_2_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 31)
        self.assertIn("Scholar's Specs", {row["name"] for row in rows})
        self.assertIn("Stellar Fan", {row["name"] for row in rows})
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_010_alltrades_present"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_2_rank_3_preserves_qualifiers(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.prerequisite_json,
                a.available_from_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v2_rank_3_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 33)
        by_name = {row["name"]: row for row in rows}
        self.assertIn("Lucky Panel or enemy drop", by_name["Staff of Salvation"]["locator"])
        self.assertEqual(
            json.loads(by_name["Staff of Salvation"]["prerequisite_json"])["source_qualifier"],
            "Lucky Panel or enemy drop",
        )
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_010_alltrades_present"
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_1_rank_1_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.time_period, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v1_rank_1_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 23)
        names = {row["name"] for row in rows}
        self.assertIn("Bamboo Spear", names)
        self.assertIn("Wayfarer's Clothes", names)
        self.assertIn("Slime Earring", names)
        self.assertTrue(all(row["time_period"] == "Past" for row in rows))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_009_alltrades"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_1_rank_2_preserves_scope_and_exclusivity(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.prerequisite_json, a.time_period,
                a.available_from_checkpoint_id, a.unavailable_after_checkpoint_id,
                lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v1_rank_2_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 31)
        by_name = {row["name"]: row for row in rows}
        self.assertIn("Iron Claws", by_name)
        self.assertIn("Lucky Panel exclusive", by_name["Cottontail Costume"]["locator"])
        self.assertEqual(
            json.loads(by_name["Cottontail Costume"]["prerequisite_json"])["source_qualifier"],
            "Lucky Panel exclusive",
        )
        self.assertIn("Scale Armour", by_name)
        self.assertNotIn("Slime Earring", by_name)
        self.assertTrue(all(row["time_period"] == "Past" for row in rows))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_009_alltrades"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

        active_ranks = self.connection.execute(
            """SELECT json_extract(a.prerequisite_json, '$.rank') AS rank
            FROM item_acquisition_paths a
            WHERE a.item_id='item_slime_earring'
              AND a.method='lucky_panel' AND a.time_period='Past'
              AND json_extract(a.prerequisite_json, '$.panel_version')=1"""
        ).fetchall()
        self.assertEqual([row["rank"] for row in active_ranks], [1])
        historical = self.connection.execute(
            """SELECT confidence, verification_status FROM claims
            WHERE claim_id='claim_slime_earring_v1_rank2_legacy_seed'"""
        ).fetchone()
        self.assertEqual(historical["confidence"], "low")
        self.assertIn("contradicted", historical["verification_status"])
        resolutions = self.connection.execute(
            """SELECT status, resolution_claim_id, rationale FROM conflicts
            WHERE conflict_key LIKE
              'item:slime_earring|lucky_panel_pool_rank|%'"""
        ).fetchall()
        self.assertEqual(len(resolutions), 3)
        self.assertTrue(all(row["status"] == "resolved" for row in resolutions))
        self.assertTrue(all("Rank 1" in row["rationale"] for row in resolutions))

    def test_lucky_panel_version_1_rank_3_preserves_names_and_timing(self):
        rows = self.connection.execute(
            """SELECT i.name, a.time_period, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v1_rank_3_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 19)
        names = {row["name"] for row in rows}
        self.assertIn("Stellar Fan", names)
        self.assertIn("Steel Fangs", names)
        self.assertIn("Magic Vetment", names)
        self.assertTrue(all(row["time_period"] == "Past" for row in rows))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_009_alltrades"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_item_report_includes_shop_price_and_alternate_panel_routes(self):
        crackers, cracker_routes = load_item_routes(self.db_path, "Pilchard Crackers")
        self.assertEqual(crackers["heroic_hoarder_required"], 1)
        self.assertEqual(cracker_routes[0]["price"], 5)
        costume, costume_routes = load_item_routes(
            self.db_path, "item_cottontail_costume"
        )
        self.assertEqual(costume["name"], "Cottontail Costume")
        self.assertEqual(len(costume_routes), 2)
        self.assertTrue(all(row["method"] == "lucky_panel" for row in costume_routes))

    def test_purchase_advice_preserves_unknown_and_free_routes(self):
        _, crackers, cracker_verdict = load_purchase_advice(
            self.db_path, "Pilchard Crackers", "cp_001_prologue"
        )
        self.assertEqual(crackers[0]["cost_status"], "paid")
        self.assertTrue(cracker_verdict.startswith("NO VERIFIED FREE ROUTE"))
        _, costume, costume_verdict = load_purchase_advice(
            self.db_path, "Cottontail Costume", "cp_001_prologue"
        )
        self.assertTrue(all(row["cost_status"] == "free" for row in costume))
        self.assertTrue(costume_verdict.startswith("CAN WAIT"))
        _, cautery, cautery_verdict = load_purchase_advice(
            self.db_path, "Cautery Sword", "cp_009_alltrades"
        )
        free_chest = next(row for row in cautery if row["method"] == "chest")
        self.assertEqual(free_chest["timing_status"], "available_now")
        self.assertNotIn("acquisition evidence conflict", cautery_verdict)

    def test_new_equipment_routes_preserve_free_and_unknown_timing(self):
        _, mask_routes, mask_verdict = load_purchase_advice(
            self.db_path, "Iron Mask", "cp_009_alltrades"
        )
        closet = next(row for row in mask_routes if row["method"] == "other")
        self.assertEqual((closet["timing_status"], closet["cost_status"]),
                         ("available_now", "free"))
        self.assertTrue(mask_verdict.startswith("DON'T BUY FOR COMPLETION"))
        _, armour_routes, armour_verdict = load_purchase_advice(
            self.db_path, "Iron Armour", "cp_009_alltrades"
        )
        drops = [row for row in armour_routes if row["method"] == "drop"]
        self.assertTrue(drops)
        self.assertTrue(all(row["timing_status"] == "unknown_gate" for row in drops))
        self.assertTrue(armour_verdict.startswith("DON'T BUY FOR COMPLETION"))
        _, platinum_routes, platinum_verdict = load_purchase_advice(
            self.db_path, "Platinum Shield", "cp_022_almighty"
        )
        basement = next(row for row in platinum_routes if row["method"] == "chest")
        self.assertEqual((basement["timing_status"], basement["cost_status"]),
                         ("available_now", "free"))
        self.assertTrue(platinum_verdict.startswith("DON'T BUY FOR COMPLETION"))
        _, aeras_routes, aeras_verdict = load_purchase_advice(
            self.db_path, "Aeras Shield", "cp_028_cathedral_of_blight"
        )
        reward = next(row for row in aeras_routes if row["method"] == "reward")
        self.assertEqual((reward["timing_status"], reward["cost_status"]),
                         ("available_now", "free"))
        self.assertTrue(aeras_verdict.startswith("DON'T BUY FOR COMPLETION"))

    def test_sledgehammer_early_power_tradeoff_is_two_source_verified(self):
        claims = self.connection.execute(
            """SELECT predicate, value_json, source_id, confidence
            FROM claims
            WHERE subject_key = 'item:sledgehammer'
              AND predicate IN ('attack_bonus', 'agility_bonus')
            ORDER BY predicate, source_id"""
        ).fetchall()
        self.assertEqual(len(claims), 4)
        self.assertEqual({row["source_id"] for row in claims}, {
            "game8_sledgehammer", "gamewith_sledgehammer"
        })
        self.assertTrue(all(row["confidence"] == "verified" for row in claims))
        values = {(row["predicate"], json.loads(row["value_json"])) for row in claims}
        self.assertEqual(values, {("attack_bonus", 26), ("agility_bonus", -20)})

        advice = self.connection.execute(
            """SELECT advice_text, applicability_json, confidence
            FROM checkpoint_advice WHERE advice_id = 'advice_cp005_fixed_weapon_sweep'"""
        ).fetchone()
        self.assertIn("+26 Attack, -20 Agility", advice["advice_text"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(json.loads(advice["applicability_json"])["sledgehammer_stats"],
                         {"attack_bonus": 26, "agility_bonus": -20})

    def test_sourced_documents_have_locators(self):
        rows = self.connection.execute(
            """SELECT document_id FROM documents
            WHERE source_id IS NOT NULL AND (locator IS NULL OR trim(locator) = '')"""
        ).fetchall()
        self.assertEqual(rows, [])

    def test_cp009_hero_power_gear_is_two_source_verified(self):
        cautery = self.connection.execute(
            """SELECT predicate, value_json, source_id, confidence
            FROM claims
            WHERE subject_key = 'item:cautery_sword'
              AND predicate IN ('attack_bonus', 'battle_use_effect')
            ORDER BY predicate, source_id"""
        ).fetchall()
        self.assertEqual(len(cautery), 4)
        self.assertEqual({row["source_id"] for row in cautery}, {
            "game8_cautery_sword", "dnavi_weapon_list"
        })
        self.assertTrue(all(row["confidence"] == "verified" for row in cautery))
        self.assertEqual(
            {(row["predicate"], json.loads(row["value_json"])) for row in cautery},
            {("attack_bonus", 42),
             ("battle_use_effect", "Scorching flames damage one enemy group")},
        )

        recommendations = self.connection.execute(
            """SELECT value_json, source_id, confidence FROM claims
            WHERE subject_key = 'checkpoint:cp_009_alltrades'
              AND predicate = 'recommended_hero_early_equipment'
            ORDER BY source_id"""
        ).fetchall()
        self.assertEqual({row["source_id"] for row in recommendations}, {
            "game8_best_equipment", "altema_best_equipment"
        })
        self.assertEqual(len({row["value_json"] for row in recommendations}), 1)
        self.assertTrue(all(row["confidence"] == "verified"
                            for row in recommendations))

        advice = self.connection.execute(
            """SELECT advice_text, applicability_json, confidence,
                verification_status
            FROM checkpoint_advice
            WHERE advice_id = 'advice_cp009_hero_practical_gear'"""
        ).fetchone()
        self.assertIn("+42 Attack", advice["advice_text"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertTrue(advice["verification_status"].startswith("two_independent"))
        applicability = json.loads(advice["applicability_json"])
        self.assertEqual(applicability["cautery_sword_stats"]["attack_bonus"], 42)
        self.assertEqual(applicability["corroboration"]["source_id"],
                         "altema_best_equipment")

    def test_ingested_medal_numbers_are_contiguous(self):
        numbers = [
            row[0]
            for row in self.connection.execute(
                "SELECT medal_number FROM mini_medal_locations ORDER BY medal_number"
            )
        ]
        self.assertEqual(numbers, list(range(1, 101)))

    def test_medal_report_respects_later_key_gates(self):
        rows = medals_available_through(self.db_path, "cp_009_alltrades")
        numbers = {row["medal_number"] for row in rows}
        self.assertIn(6, numbers)
        self.assertNotIn(3, numbers)
        self.assertNotIn(5, numbers)
        self.assertNotIn(7, numbers)

    def test_verified_medals_retain_independent_evidence(self):
        verified = self.connection.execute(
            """SELECT medal_number FROM mini_medal_locations
            WHERE verification_status LIKE 'cross_source_checked%'
            ORDER BY medal_number"""
        ).fetchall()
        evidence = self.connection.execute(
            """SELECT DISTINCT medal_number FROM mini_medal_evidence
            WHERE source_id = 'rpgsite_walkthrough'
            ORDER BY medal_number"""
        ).fetchall()
        self.assertEqual(verified, evidence)

    def test_all_medals_have_direct_independent_evidence(self):
        indexed = self.connection.execute(
            """SELECT medal_number, verification_status FROM mini_medal_locations
            WHERE verification_status LIKE 'search_index_checked%'
            ORDER BY medal_number"""
        ).fetchall()
        self.assertEqual(indexed, [])

    def test_checkpoint_sequences_are_contiguous(self):
        sequences = [
            row[0]
            for row in self.connection.execute(
                "SELECT sequence_no FROM checkpoints ORDER BY sequence_no"
            )
        ]
        self.assertEqual(sequences, list(range(1, len(sequences) + 1)))

    def test_vocation_requirement_ids_are_stable(self):
        groups = {
            row[0]
            for row in self.connection.execute(
                "SELECT DISTINCT group_id FROM vocation_requirements"
            )
        }
        self.assertIn("req_gladiator", groups)
        self.assertIn("req_hero", groups)
        self.assertFalse(any(group.startswith("req_group_") for group in groups))

    def test_player_state_is_valid_json_and_unknown_by_default(self):
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"))
        self.assertIsNone(state["story"]["checkpoint_id"])
        self.assertEqual(state["source_type"], "player_report")
        self.assertNotIn("item_quantities", state["completion"])

    def test_optional_item_quantity_ledger_rejects_false_precision(self):
        base = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            for invalid in (
                [], {"item_rabbit_tail": -1}, {"item_rabbit_tail": True},
                {"item_rabbit_tail": 1.5},
            ):
                state = json.loads(json.dumps(base))
                state["completion"]["item_quantities"] = invalid
                path.write_text(json.dumps(state), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "item_quantities"):
                    _load_state(path)
            state = json.loads(json.dumps(base))
            state["completion"]["item_quantities"] = {
                "item_rabbit_tail": 0,
                "item_meteorite_bracer": 2,
            }
            path.write_text(json.dumps(state), encoding="utf-8")
            self.assertEqual(_load_state(path)["completion"]["item_quantities"]
                             ["item_meteorite_bracer"], 2)

    def test_player_state_update_targets_explicit_file(self):
        source = ROOT / "player" / "ryan-save-state.json"
        state_path = Path(self.tempdir.name) / "player-state.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        update_state(state_path, "party.members.Hero.level", "12")

        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["party"]["members"]["Hero"]["level"], 12)
        self.assertIsNotNone(state["last_updated"])

    def test_player_state_update_rejects_unknown_path(self):
        source = ROOT / "player" / "ryan-save-state.json"
        state_path = Path(self.tempdir.name) / "player-state-invalid.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        with self.assertRaises(KeyError):
            update_state(state_path, "party.members.Hero.unknown", "12")

    def test_player_state_update_accepts_json_list_and_rejects_type_change(self):
        source = ROOT / "player" / "ryan-save-state.json"
        state_path = Path(self.tempdir.name) / "player-state-list.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        update_state(state_path, "completion.mini_medals_found", "[1, 2]")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["mini_medals_found"], [1, 2])
        with self.assertRaises(TypeError):
            update_state(state_path, "completion.mini_medals_found", "not-a-list")

    def test_checkpoint_report_surfaces_stop_warning_and_medals(self):
        report = load_report(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_001_prologue",
        )
        stops = [row for row in report["obligations"] if row["stop_before_advancing"]]
        self.assertEqual([row["subject"] for row in stops], ["Pearl's Fish Bits"])
        self.assertEqual([row["medal_number"] for row in report["medals"]], [6, 7])
        self.assertGreater(report["open_completion_ledger_count"], 0)
        self.assertIn("checkpoint_missables", report["completion_ledger_counts"])
        self.assertFalse(report["player_checkpoint_matches"])

    def test_checkpoint_report_requires_known_checkpoint(self):
        with self.assertRaises(ValueError):
            load_report(
                self.db_path,
                ROOT / "player" / "ryan-save-state.json",
                "cp_missing",
            )

    def test_checkpoint_report_hides_recorded_obligations_and_medals(self):
        state_path = Path(self.tempdir.name) / "checkpoint-report-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["obligations_completed"] = ["obl_prologue_fish_bits"]
        state["completion"]["mini_medals_found"] = [6, 7]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_report(self.db_path, state_path, "cp_001_prologue")
        self.assertFalse(any(row["stop_before_advancing"]
                             for row in report["obligations"]))
        self.assertEqual(report["medals"], [])
        self.assertEqual(report["completed_hidden_count"], 1)
        self.assertEqual(report["found_medals_hidden_count"], 2)

    def test_early_walkthrough_orders_range_and_classifies_medals(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
        )
        self.assertEqual(
            [row["checkpoint"]["sequence_no"] for row in report["blocks"]],
            list(range(1, 10)),
        )
        prologue = report["blocks"][0]
        self.assertEqual([row["subject"] for row in prologue["stops"]], ["Pearl's Fish Bits"])
        self.assertEqual(prologue["medals_now"], [])
        self.assertEqual(
            [row["medal_number"] for row in prologue["medals_later"]], [6, 7]
        )
        alltrades = report["blocks"][-1]
        alltrades_subjects = [row["subject"] for row in alltrades["now"]]
        self.assertEqual(
            alltrades_subjects,
            [
                "Alltrades route Blue Fragments",
                "Proficient Paneller and Platinum Paneller",
                "Lucky Panel Version 1 Cottontail Costume and Elevating Shoes",
                "Pilgrim's Perdition through Dungeon of Descent finite pickups",
                "Alltrades Key and Tunnel to the Abbey fixed loot",
                "Allblades Arena vocation access and fixed pickups",
                "Restored Alltrades Abbey pickups",
                "Thief's Key and immediate backtracking",
            ],
        )
        self.assertIn(6, [row["medal_number"] for row in alltrades["medals_backtrack"]])
        self.assertNotIn(7, [row["medal_number"] for row in alltrades["medals_backtrack"]])
        self.assertTrue(alltrades["guidance"])

    def test_early_walkthrough_hides_collected_medals(self):
        state_path = Path(self.tempdir.name) / "walkthrough-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["mini_medals_found"] = [6]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_walkthrough(self.db_path, state_path)
        all_medals = [
            row["medal_number"]
            for block in report["blocks"]
            for bucket in ("medals_now", "medals_backtrack", "medals_later")
            for row in block[bucket]
        ]
        self.assertNotIn(6, all_medals)
        self.assertEqual(report["collected_medal_count"], 1)

    def test_walkthrough_generalizes_through_cp033(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_010_alltrades_present",
            "cp_033_arena_achievement_cleanup",
        )
        self.assertEqual(
            [block["checkpoint"]["sequence_no"] for block in report["blocks"]],
            list(range(10, 34)),
        )
        for block in report["blocks"]:
            orders = [row["display_order"] for row in block["stops"] + block["now"]]
            self.assertTrue(all(isinstance(order, int) and order > 0 for order in orders))
            self.assertEqual(len(orders), len(set(orders)))

        flying_carpet = report["blocks"][3]
        self.assertIn(
            5, [row["medal_number"] for row in flying_carpet["medals_backtrack"]]
        )
        self.assertNotIn(
            3, [row["medal_number"] for row in flying_carpet["medals_backtrack"]]
        )

        roamer_return = report["blocks"][2]
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough({**report, "blocks": [roamer_return]})
        self.assertIn("seed_partial", output.getvalue())
        self.assertIn("partial audit; not a guarantee", output.getvalue())
        self.assertIn("guidance not normalized", output.getvalue())

    def test_postgame_walkthrough_tracks_all_final_medals_and_no_fake_stops(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_030_postgame_another_world",
            "cp_033_arena_achievement_cleanup",
        )
        self.assertEqual(
            [block["checkpoint"]["sequence_no"] for block in report["blocks"]],
            [30, 31, 32, 33],
        )
        self.assertTrue(all(not block["stops"] for block in report["blocks"]))
        medal_numbers = {
            row["medal_number"]
            for block in report["blocks"]
            for bucket in ("medals_now", "medals_backtrack", "medals_later")
            for row in block[bucket]
        }
        self.assertTrue(set(range(95, 101)).issubset(medal_numbers))
        self.assertEqual(len(report["blocks"][2]["now"]), 11)
        self.assertEqual(len(report["blocks"][3]["now"]), 8)

    def test_walkthrough_wrapper_preserves_legacy_entry_point(self):
        self.assertIs(walkthrough_main, early_walkthrough_main)

    def test_walkthrough_rejects_requested_unordered_checkpoint(self):
        unordered_db = Path(self.tempdir.name) / "unordered-walkthrough.sqlite"
        build_database(unordered_db)
        with sqlite3.connect(unordered_db) as connection:
            connection.execute(
                """UPDATE checkpoint_obligations SET display_order = NULL
                WHERE checkpoint_id = 'cp_010_alltrades_present'"""
            )
        with self.assertRaisesRegex(ValueError, "not ordered yet"):
            load_walkthrough(
                unordered_db,
                ROOT / "player" / "ryan-save-state.json",
                "cp_010_alltrades_present",
                "cp_010_alltrades_present",
            )

    def test_cp010_progress_uses_stable_order(self):
        state_path = Path(self.tempdir.name) / "cp010-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "done", ["cp_010_alltrades_present", "1"]
        )
        report = load_walkthrough(
            self.db_path,
            state_path,
            "cp_010_alltrades_present",
            "cp_010_alltrades_present",
        )
        remaining = [row["display_order"] for row in report["blocks"][0]["now"]]
        self.assertNotIn(1, remaining)
        self.assertTrue(all(order > 1 for order in remaining))

    def test_early_walkthrough_rejects_bad_ranges_and_state(self):
        state_path = ROOT / "player" / "ryan-save-state.json"
        with self.assertRaises(ValueError):
            load_walkthrough(
                self.db_path, state_path, "cp_009_alltrades", "cp_001_prologue"
            )
        with self.assertRaises(ValueError):
            load_walkthrough(self.db_path, state_path, "cp_missing", "cp_009_alltrades")
        bad_state_path = Path(self.tempdir.name) / "walkthrough-bad-state.json"
        state = json.loads(state_path.read_text())
        state["completion"]["mini_medals_found"] = "unknown"
        bad_state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_walkthrough(self.db_path, bad_state_path)

    def test_early_walkthrough_sources_are_opt_in(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_001_prologue",
            "cp_001_prologue",
        )
        terse = io.StringIO()
        with redirect_stdout(terse):
            print_walkthrough(report)
        self.assertIn("medal tracking unknown", terse.getvalue())
        self.assertNotIn("Source:", terse.getvalue())
        self.assertNotIn("Medals NOW:", terse.getvalue())
        self.assertIn("Medals LATER:", terse.getvalue())

        sourced = io.StringIO()
        with redirect_stdout(sourced):
            print_walkthrough(report, include_sources=True)
        self.assertIn("Source:", sourced.getvalue())
        self.assertIn("https://game8.co/", sourced.getvalue())

    def test_checkpoint_advice_filters_orders_and_renders_goals(self):
        advice_db = Path(self.tempdir.name) / "walkthrough-advice.sqlite"
        build_database(advice_db)
        with sqlite3.connect(advice_db) as connection:
            rows = [
                ("advice_test_boss", "boss", "Test Boss", "Guard, then strike.",
                 "completion_safe", 91, 1),
                ("advice_test_gear", "gear", "Hero", "Equip the test sword.",
                 "immediate_power", 91, 1),
                ("advice_test_hidden", "grind", "Slimes", "Unverified loop.",
                 "both", 91, 0),
            ]
            connection.executemany(
                """INSERT INTO checkpoint_advice(
                    advice_id, checkpoint_id, advice_type, subject, advice_text,
                    recommendation_goal, display_order, applicability_json,
                    ready_for_play, source_id, locator, confidence,
                    verification_status
                ) VALUES (?, 'cp_009_alltrades', ?, ?, ?, ?, ?, '{}', ?,
                    'game8_best_equipment', 'Test locator', 'high', 'source_checked')""",
                rows,
            )
        report = load_walkthrough(
            advice_db,
            ROOT / "player" / "ryan-save-state.json",
            "cp_009_alltrades",
            "cp_009_alltrades",
        )
        advice = report["blocks"][0]["advice"]
        fixture_advice = [
            row for row in advice if row["advice_id"].startswith("advice_test_")
        ]
        self.assertEqual(
            [row["advice_type"] for row in fixture_advice], ["gear", "boss"]
        )
        terse = io.StringIO()
        with redirect_stdout(terse):
            print_walkthrough(report)
        self.assertIn("Hero — Equip the test sword. (power)", terse.getvalue())
        self.assertIn("Test Boss — Guard, then strike. (safe)", terse.getvalue())
        self.assertNotIn("Unverified loop", terse.getvalue())
        self.assertNotIn("Source:", terse.getvalue())
        sourced = io.StringIO()
        with redirect_stdout(sourced):
            print_walkthrough(report, include_sources=True)
        self.assertIn("Source:", sourced.getvalue())
        self.assertIn("Test locator", sourced.getvalue())

    def test_threshold_advice_remains_conditional_when_medals_unknown(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_007_frobisher",
            "cp_007_frobisher",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report)
        self.assertIn("If you have 15 medals", output.getvalue())

    def test_la_bravoure_surfaces_two_source_metal_grind_without_fake_rate(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_011_la_bravoure",
            "cp_011_la_bravoure",
        )
        rows = {row["subject"]: row for row in report["blocks"][0]["advice"]
                if row["advice_type"] == "grind"}
        self.assertEqual(set(rows), {
            "Optional Metal King Slime grind",
            "Rabbit Tail drop-farm setup",
        })
        metal = rows["Optional Metal King Slime grind"]
        self.assertEqual(metal["confidence"], "verified")
        self.assertEqual(metal["verification_status"],
                         "two_source_verified_repeatable_location_and_critical_tactic_rate_and_ceiling_unknown")
        applicability = json.loads(metal["applicability_json"])
        self.assertEqual(applicability["time_period"], "Present")
        self.assertEqual(applicability["rate"], "unknown")
        self.assertEqual(applicability["ceiling"], "unknown")
        rabbit = rows["Rabbit Tail drop-farm setup"]
        rabbit_scope = json.loads(rabbit["applicability_json"])
        self.assertIn("Only equip copies explicitly owned",
                      rabbit_scope["quantity_guard"])
        self.assertIn("per-copy drop increase", rabbit_scope["unknowns"])
        self.assertIn("reserve-member copies do not apply",
                      rabbit_scope["single_source_constraint"])
        claim_rows = self.connection.execute(
            """SELECT c.predicate, c.value_json, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.claim_id IN (
                'claim_rabbit_tail_effect_stacking_appmedia',
                'claim_rabbit_tail_effect_stacking_gamewith',
                'claim_rabbit_tail_reserve_inactive_appmedia')"""
        ).fetchall()
        self.assertEqual(len(claim_rows), 3)
        self.assertEqual({row["publisher"] for row in claim_rows},
                         {"AppMedia", "GameWith"})
        reserve = next(row for row in claim_rows
                       if row["predicate"] == "effect_party_position_scope")
        self.assertIn("reserve members do not", json.loads(reserve["value_json"]))

    def test_checkpoint_advice_requires_object_applicability(self):
        normalized = normalize_checkpoint_advice([
            {"advice_id": "ok", "applicability": {"difficulty": "normal"}}
        ])
        self.assertEqual(
            json.loads(normalized[0]["applicability_json"]),
            {"difficulty": "normal"},
        )
        with self.assertRaises(ValueError):
            normalize_checkpoint_advice([
                {"advice_id": "bad", "applicability": ["normal"]}
            ])

    def test_checkpoint_advice_two_source_requires_independent_publishers(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """CREATE TABLE sources(source_id TEXT PRIMARY KEY, publisher TEXT);
            CREATE TABLE claims(
                claim_id TEXT PRIMARY KEY,
                source_id TEXT REFERENCES sources(source_id)
            );
            CREATE TABLE checkpoint_advice(
                advice_id TEXT PRIMARY KEY,
                applicability_json TEXT NOT NULL,
                verification_status TEXT NOT NULL
            );"""
        )
        connection.executemany(
            "INSERT INTO sources VALUES (?, ?)",
            [("page_a", "Same Publisher"), ("page_b", "Same Publisher")],
        )
        connection.executemany(
            "INSERT INTO claims VALUES (?, ?)",
            [("claim_a", "page_a"), ("claim_b", "page_b")],
        )
        connection.execute(
            "INSERT INTO checkpoint_advice VALUES (?, ?, ?)",
            ("advice_same_publisher",
             json.dumps({"evidence_claim_ids": ["claim_a", "claim_b"]}),
             "two_source_verified"),
        )
        with self.assertRaisesRegex(ValueError, "without two claim publishers"):
            validate_checkpoint_advice_evidence(connection)
        connection.execute(
            "UPDATE sources SET publisher='Independent Publisher' WHERE source_id='page_b'"
        )
        validate_checkpoint_advice_evidence(connection)
        connection.execute(
            "UPDATE checkpoint_advice SET applicability_json=?",
            (json.dumps({"evidence_claim_ids": ["claim_a", "missing_claim"]}),),
        )
        with self.assertRaisesRegex(ValueError, "missing evidence claims"):
            validate_checkpoint_advice_evidence(connection)
        connection.close()

    def test_meteorite_bracer_duplicate_power_is_item_specific_and_quantity_guarded(self):
        claims = self.connection.execute(
            """SELECT claim_id, predicate, source_id, value_json
            FROM claims
            WHERE claim_id LIKE 'claim_meteorite_bracer_%'
            ORDER BY claim_id"""
        ).fetchall()
        self.assertEqual(len(claims), 4)
        self.assertEqual({row["source_id"] for row in claims},
                         {"koshian_almighty_speedrun", "game8_jp_aishe_build"})
        self.assertEqual({row["predicate"] for row in claims},
                         {"same_item_equip_legality", "duplicate_effect_stacking"})
        numeric = next(json.loads(row["value_json"]) for row in claims
                       if row["claim_id"] ==
                       "claim_meteorite_bracer_additive_agility_koshian")
        self.assertEqual(numeric["two_copy_agility"], 200)

        advice = self.connection.execute(
            """SELECT checkpoint_id, advice_text, applicability_json,
                      verification_status
            FROM checkpoint_advice
            WHERE advice_id='advice_cp030_aishe_double_meteorite'"""
        ).fetchone()
        self.assertEqual(advice["checkpoint_id"], "cp_030_postgame_another_world")
        self.assertIn("+200 Agility", advice["advice_text"])
        scope = json.loads(advice["applicability_json"])
        self.assertEqual(scope["copies_required"], 2)
        self.assertIn("binary collection ledger does not prove quantity",
                      scope["quantity_guard"])
        self.assertIn("no universal duplicate-accessory", scope["scope"])
        self.assertEqual(advice["verification_status"],
                         "two_publisher_meteorite_specific_duplicate_legality_and_additive_stat_stacking")

    def test_alltrades_boss_and_vocation_advice_is_chronological(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_009_alltrades",
            "cp_009_alltrades",
        )
        advice = report["blocks"][0]["advice"]
        bosses = [row["subject"] for row in advice if row["advice_type"] == "boss"]
        self.assertEqual(
            bosses,
            [
                "Arena 1: Numpton's Numpties",
                "Arena 2: Bronson and the Bristles",
                "Arena 3: Hans and the Hands",
                "Arena 4: Nava's Knaves",
                "Cardinal Sin",
                "Rashers and Stripes",
            ],
        )
        self.assertEqual(
            len([row for row in advice if row["advice_type"] == "vocation"]), 2
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report)
        rendered = output.getvalue()
        self.assertLess(rendered.index("Boss:"), rendered.index("NOW:"))
        self.assertLess(rendered.index("Vocations:"), rendered.index("NOW:"))
        self.assertNotIn("CONFLICT: Cautery Sword — precise location description disputed", rendered)
        self.assertNotIn("CONFLICT: Iron Shield — purchase price disputed", rendered)
        self.assertNotIn("Source A:", rendered)
        sourced = io.StringIO()
        with redirect_stdout(sourced):
            print_walkthrough(report, include_sources=True)
        self.assertIn("https://", sourced.getvalue())

    def test_first_ten_hours_cover_all_direct_boss_sequences(self):
        rows = self.connection.execute(
            """SELECT advice_id, checkpoint_id, subject, display_order, source_id,
                locator, verification_status
            FROM checkpoint_advice
            WHERE advice_id IN (
                'advice_cp002_tribulators', 'advice_cp003_golem',
                'advice_cp003_crabble_maeve_sequence',
                'advice_cp007_tinpot_dictator', 'advice_cp007_slaughtomaton',
                'advice_cp008_florin', 'advice_cp008_guardians_roamers')
            ORDER BY checkpoint_id, display_order"""
        ).fetchall()
        self.assertEqual([row["subject"] for row in rows], [
            "Tribulators", "Golem", "Crabble-Rouser and Maeve",
            "Tinpot Dictator", "Slaughtomaton", "Florin",
            "Guardians of the Roamers",
        ])
        self.assertTrue(all(row["source_id"].startswith("game8_") for row in rows))
        self.assertTrue(all(row["locator"] for row in rows))
        self.assertTrue(all(
            row["verification_status"] == "source_checked" or
            row["verification_status"].startswith("single_independent_source") or
            row["verification_status"].startswith("two_independent_current_version_sources") or
            "two_source_verified" in row["verification_status"] or
            row["verification_status"].startswith("core_") and
            "two_source_verified" in row["verification_status"]
            for row in rows
        ))

    def test_early_boss_tactics_preserve_source_diversity_and_single_source_limits(self):
        claims = self.connection.execute(
            """SELECT predicate, confidence, verification_status
               FROM claims
               WHERE claim_id IN (
                 'claim_golem_physical_buff_game8',
                 'claim_golem_physical_buff_noobfeed',
                 'claim_golem_fire_weakness_thegameslayer',
                 'claim_crabble_plan_game8', 'claim_crabble_plan_noobfeed',
                 'claim_maeve_plan_game8', 'claim_maeve_plan_noobfeed',
                 'claim_maeve_dazzle_resistance_game8',
                 'claim_tinpot_plan_game8', 'claim_tinpot_plan_noobfeed')
               ORDER BY claim_id"""
        ).fetchall()
        self.assertEqual(len(claims), 10)
        verified = [row for row in claims if row["verification_status"] ==
                    "two_independent_current_version_sources"]
        self.assertEqual(len(verified), 8)
        provisional = [row for row in claims if
                       row["verification_status"].startswith("single_")]
        self.assertEqual({row["predicate"] for row in provisional},
                         {"elemental_weakness", "dazzle_susceptibility"})
        self.assertTrue(all(row["confidence"] == "high" for row in provisional))
        advice = self.connection.execute(
            """SELECT advice_id, applicability_json, confidence,
                      verification_status
               FROM checkpoint_advice WHERE advice_id IN (
                 'advice_cp003_golem',
                 'advice_cp003_crabble_maeve_sequence',
                 'advice_cp007_tinpot_dictator')"""
        ).fetchall()
        self.assertEqual(len(advice), 3)
        self.assertTrue(all(row["confidence"] == "verified" for row in advice))
        self.assertTrue(all("two_source_verified" in row["verification_status"]
                            for row in advice))
        notes = {row["advice_id"]:
                 json.loads(row["applicability_json"])["evidence_note"]
                 for row in advice}
        self.assertIn("exact role split", notes["advice_cp003_golem"])
        self.assertIn("Dazzle resistance",
                      notes["advice_cp003_crabble_maeve_sequence"])
        self.assertIn("Kiefer Let Loose",
                      notes["advice_cp007_tinpot_dictator"])

    def test_cp001_through_cp009_two_source_advice_has_atomic_evidence_links(self):
        expected = {
            "advice_cp002_tribulators", "advice_cp003_golem",
            "advice_cp003_crabble_maeve_sequence",
            "advice_cp003_vicious_hearts_are_finite",
            "advice_cp004_glowering_inferno", "advice_cp005_hackrobat",
            "advice_cp005_fixed_weapon_sweep",
            "advice_cp007_tinpot_dictator", "advice_cp007_slaughtomaton",
            "advice_cp007_windcheater_spike", "advice_cp008_florin",
            "advice_cp008_magic_shield_spike",
            "advice_cp008_guardians_roamers",
            "advice_cp008_roamer_metal_slime_grind",
            "advice_cp009_hero_practical_gear",
            "advice_cp009_ruff_practical_gear",
            "advice_cp009_maribel_practical_gear",
            "advice_cp009_snooze_stick_sealed_use",
            "advice_cp009_cardinal_sin",
            "advice_cp009_arena_numpton", "advice_cp009_arena_bronson",
            "advice_cp009_arena_hans", "advice_cp009_arena_nava",
            "advice_cp009_vocations_arena_power",
            "advice_cp009_vocations_prerequisite_progress",
            "advice_cp009_rashers_stripes",
        }
        rows = self.connection.execute(
            """SELECT advice_id, applicability_json, verification_status
               FROM checkpoint_advice
               WHERE CAST(substr(checkpoint_id, 4, 3) AS INTEGER) <= 9
                 AND (verification_status LIKE '%two_source%'
                      OR verification_status LIKE '%two_independent%')"""
        ).fetchall()
        self.assertEqual({row["advice_id"] for row in rows}, expected)
        mixed = 0
        for row in rows:
            claim_ids = json.loads(row["applicability_json"])[
                "evidence_claim_ids"]
            self.assertGreaterEqual(len(claim_ids), 2, row["advice_id"])
            placeholders = ",".join("?" for _ in claim_ids)
            claims = self.connection.execute(
                f"""SELECT claim_id, source_id, verification_status
                    FROM claims WHERE claim_id IN ({placeholders})""", claim_ids
            ).fetchall()
            self.assertEqual(len(claims), len(set(claim_ids)), row["advice_id"])
            self.assertGreaterEqual(len({claim["source_id"] for claim in claims}),
                                    2, row["advice_id"])
            self.assertTrue(all(not claim["verification_status"].startswith(
                "single_") for claim in claims), row["advice_id"])
            if "single_source" in row["verification_status"]:
                mixed += 1
        self.assertGreater(mixed, 0)

    def test_glowering_inferno_phase_plan_is_corroborated_without_promoting_single_source_defend(self):
        claims = self.connection.execute(
            """SELECT claim_id, predicate, confidence, verification_status
               FROM claims
               WHERE claim_id LIKE 'claim_glowering_%'
               ORDER BY claim_id"""
        ).fetchall()
        self.assertEqual(len(claims), 9)
        verified = [row for row in claims if row["verification_status"] ==
                    "two_independent_current_version_sources"]
        self.assertEqual(len(verified), 8)
        provisional = [row for row in claims if
                       row["verification_status"] == "single_independent_source"]
        self.assertEqual(len(provisional), 1)
        self.assertEqual(provisional[0]["predicate"],
                         "recommended_muster_strength_response")
        self.assertEqual(provisional[0]["confidence"], "high")
        advice = self.connection.execute(
            """SELECT advice_text, confidence, verification_status
               FROM checkpoint_advice
               WHERE advice_id='advice_cp004_glowering_inferno'"""
        ).fetchone()
        self.assertIn("When it glows, switch to physical attacks", advice["advice_text"])
        self.assertIn("GameWith alone", advice["advice_text"])
        self.assertEqual(advice["confidence"], "verified")
        self.assertEqual(
            advice["verification_status"],
            "core_plan_two_source_verified_single_source_muster_defend")

    def test_remaining_allblades_rounds_separate_verified_core_from_nava_options(self):
        claims = self.connection.execute(
            """SELECT claim_id, predicate, confidence, verification_status
               FROM claims
               WHERE claim_id IN (
                 'claim_bronson_plan_game8', 'claim_bronson_plan_noobfeed',
                 'claim_hans_plan_game8', 'claim_hans_plan_noobfeed',
                 'claim_nava_plan_game8', 'claim_nava_plan_noobfeed',
                 'claim_nava_repel_physical_intoindiegames',
                 'claim_nava_ruff_call_wild_intoindiegames')
               ORDER BY claim_id"""
        ).fetchall()
        self.assertEqual(len(claims), 8)
        self.assertEqual(len([row for row in claims if
                             row["verification_status"] ==
                             "two_independent_current_version_sources"]), 6)
        provisional = [row for row in claims if
                       row["verification_status"].startswith("single_")]
        self.assertEqual(len(provisional), 2)
        self.assertTrue(all(row["confidence"] == "high" for row in provisional))
        advice = self.connection.execute(
            """SELECT advice_id, confidence, verification_status
               FROM checkpoint_advice
               WHERE advice_id IN ('advice_cp009_arena_bronson',
                                   'advice_cp009_arena_hans',
                                   'advice_cp009_arena_nava')
               ORDER BY display_order"""
        ).fetchall()
        self.assertEqual([row["confidence"] for row in advice],
                         ["verified", "verified", "verified"])
        self.assertEqual(advice[0]["verification_status"],
                         "two_independent_current_version_sources")
        self.assertEqual(advice[1]["verification_status"],
                         "two_independent_current_version_sources")
        self.assertIn("single_source", advice[2]["verification_status"])

    def test_hardlypool_boss_core_is_corroborated_and_exact_tools_stay_attributed(self):
        claim_ids = (
            "claim_sunken_spirits_group_plan_game8",
            "claim_sunken_spirits_group_plan_noobfeed",
            "claim_sunken_spirits_recovery_timing_game8",
            "claim_sunken_spirits_recovery_gamerzenith",
            "claim_sunken_spirits_recovery_kotanespinosa",
            "claim_gracos_element_accuracy_plan_game8",
            "claim_gracos_element_accuracy_plan_noobfeed",
            "claim_gracos_dazzle_game8",
            "claim_king_slime_heal_seal_game8",
            "claim_king_slime_heal_seal_gamewith",
            "claim_king_slime_attack_buff_game8",
            "claim_ethereal_serpent_airborne_debuff_plan_game8",
            "claim_ethereal_serpent_airborne_debuff_plan_noobfeed",
            "claim_ethereal_serpent_flying_knee_game8",
            "claim_gracos_v_fire_buff_plan_game8",
            "claim_gracos_v_fire_buff_plan_noobfeed",
        )
        placeholders = ",".join("?" for _ in claim_ids)
        claims = self.connection.execute(
            f"""SELECT claim_id, confidence, verification_status
                FROM claims WHERE claim_id IN ({placeholders})""", claim_ids
        ).fetchall()
        self.assertEqual(len(claims), 16)
        self.assertEqual(len([row for row in claims if row["verification_status"] ==
                             "two_independent_current_version_sources"]), 10)
        provisional = [row for row in claims if
                       row["verification_status"].startswith("single_")]
        self.assertEqual(len(provisional), 4)
        self.assertTrue(all(row["confidence"] == "high" for row in provisional))
        advice = self.connection.execute(
            """SELECT advice_text, confidence, verification_status
               FROM checkpoint_advice
               WHERE advice_id IN ('advice_cp013_sunken_spirits',
                                   'advice_cp013_gracos',
                                   'advice_cp013_king_slime',
                                   'advice_cp013_ethereal_serpent',
                                   'advice_cp014_gracos_v')"""
        ).fetchall()
        self.assertEqual(len(advice), 5)
        self.assertTrue(all(row["confidence"] == "verified" for row in advice))
        self.assertTrue(all("two_source_verified" in row["verification_status"]
                            for row in advice))
        sunken = next(row for row in advice
                      if "inter_battle_heal" in row["verification_status"])
        self.assertNotIn("Conserve HP/MP", sunken["advice_text"])
        self.assertNotIn("leaving one Spirit alive", sunken["advice_text"])
        self.assertIn("MP-specific detail remains single-source", sunken["advice_text"])
        self.assertTrue(all("alone" in row["advice_text"] for row in advice
                            if row is not sunken))
        recovery_publishers = self.connection.execute(
            """SELECT COUNT(DISTINCT s.publisher) FROM claims c
            JOIN sources s USING(source_id)
            WHERE c.subject_key='encounter:sunken_spirits_to_gracos'
              AND c.predicate='inter_battle_recovery'"""
        ).fetchone()[0]
        self.assertEqual(recovery_publishers, 2)

    def test_fire_spirit_and_smothers_core_plans_separate_single_source_tools(self):
        claims = self.connection.execute(
            """SELECT claim_id, confidence, verification_status FROM claims
               WHERE claim_id LIKE 'claim_fire_spirit_%'
                  OR claim_id LIKE 'claim_smothers_%'"""
        ).fetchall()
        self.assertEqual(len(claims), 8)
        self.assertEqual(len([row for row in claims if row["verification_status"] ==
                             "two_independent_current_version_sources"]), 4)
        provisional = [row for row in claims if
                       row["verification_status"].startswith("single_")]
        self.assertEqual(len(provisional), 4)
        self.assertTrue(all(row["confidence"] == "high" for row in provisional))
        advice = self.connection.execute(
            """SELECT advice_id, advice_text, confidence, verification_status
               FROM checkpoint_advice
               WHERE advice_id IN ('advice_cp023_fire_spirit',
                                   'advice_cp023_smothers')
               ORDER BY advice_id"""
        ).fetchall()
        self.assertEqual(len(advice), 2)
        self.assertTrue(all(row["confidence"] == "verified" for row in advice))
        self.assertTrue(all("two_source_verified" in row["verification_status"]
                            for row in advice))
        self.assertTrue(all("alone" in row["advice_text"] for row in advice))

    def test_almighty_and_xenlon_core_tactics_exclude_uncorroborated_numbers(self):
        claim_ids = (
            "claim_almighty_elemental_resistance_game8",
            "claim_almighty_elemental_resistance_gamewith",
            "claim_almighty_group_recovery_game8",
            "claim_almighty_group_recovery_gamewith",
            "claim_almighty_reapply_support_game8",
            "claim_almighty_reapply_support_gamewith",
            "claim_almighty_status_cures_game8",
            "claim_almighty_rest_burst_tools_gamewith",
            "claim_xenlon_fire_ice_protection_gamewith",
            "claim_xenlon_fire_ice_protection_video",
            "claim_xenlon_healer_buffer_roles_game8",
            "claim_xenlon_healer_buffer_roles_video",
            "claim_xenlon_revive_items_game8",
            "claim_xenlon_defensive_buffs_game8",
            "claim_xenlon_breath_reflection_gamewith",
            "claim_xenlon_burst_astron_gamewith",
        )
        placeholders = ",".join("?" for _ in claim_ids)
        claims = self.connection.execute(
            f"""SELECT claim_id, confidence, verification_status FROM claims
                WHERE claim_id IN ({placeholders})""", claim_ids
        ).fetchall()
        self.assertEqual(len(claims), 16)
        verified = [row for row in claims if
                    row["verification_status"].startswith(
                        "two_independent_current_version_sources")]
        self.assertEqual(len(verified), 10)
        provisional = [row for row in claims if
                       row["verification_status"].startswith("single_")]
        self.assertEqual(len(provisional), 6)
        self.assertTrue(all(row["confidence"] == "high" for row in provisional))
        advice = self.connection.execute(
            """SELECT advice_text, confidence, verification_status
               FROM checkpoint_advice
               WHERE advice_id IN ('advice_cp030_almighty',
                                   'advice_cp032_xenlon')"""
        ).fetchall()
        self.assertEqual(len(advice), 2)
        self.assertTrue(all(row["confidence"] == "verified" for row in advice))
        self.assertTrue(all("two_source_verified" in row["verification_status"]
                            for row in advice))
        self.assertTrue(all("no_level_claim_no_turn_or_weakness_claim" in
                            row["verification_status"] for row in advice))
        self.assertTrue(all("alone" in row["advice_text"] for row in advice))

    def test_remaining_early_mid_bosses_keep_two_source_core_and_attributed_extras(self):
        claim_ids = (
            "claim_mild_bunch_rogue_control_game8",
            "claim_mild_bunch_rogue_control_gamewith",
            "claim_mild_bunch_aoe_fizzle_game8",
            "claim_mild_bunch_target_defend_gamewith",
            "claim_skeleton_squire_buff_game8",
            "claim_skeleton_squire_buff_gamewith",
            "claim_skeleton_squire_group_recovery_game8",
            "claim_skeleton_squire_group_recovery_gamewith",
            "claim_skeleton_squire_element_mp_gamewith",
            "claim_setesh_buff_game8", "claim_setesh_buff_gamewith",
            "claim_setesh_counter_heal_game8",
            "claim_setesh_counter_heal_gamewith",
            "claim_setesh_ice_gamewith", "claim_setesh_priest_game8",
            "claim_tribulators_tutorial_plan_game8",
        )
        placeholders = ",".join("?" for _ in claim_ids)
        claims = self.connection.execute(
            f"""SELECT claim_id, confidence, verification_status FROM claims
                WHERE claim_id IN ({placeholders})""", claim_ids
        ).fetchall()
        self.assertEqual(len(claims), 16)
        verified = [row for row in claims if
                    row["verification_status"].startswith(
                        "two_independent_current_version_sources")]
        self.assertEqual(len(verified), 10)
        provisional = [row for row in claims if
                       row["verification_status"].startswith("single_")]
        self.assertEqual(len(provisional), 6)
        advice = self.connection.execute(
            """SELECT advice_id, advice_text, confidence, verification_status
               FROM checkpoint_advice WHERE advice_id IN (
                 'advice_cp002_tribulators', 'advice_cp010_mild_bunch',
                 'advice_cp011_skeleton_squire', 'advice_cp011_setesh')"""
        ).fetchall()
        self.assertEqual(len(advice), 4)
        tribulators = next(row for row in advice if
                           row["advice_id"] == "advice_cp002_tribulators")
        self.assertEqual(tribulators["confidence"], "verified")
        self.assertIn("two_source_verified", tribulators["verification_status"])
        corroborated = [row for row in advice if row is not tribulators]
        self.assertTrue(all(row["confidence"] == "verified" for row in corroborated))
        self.assertTrue(all("two_source_verified" in row["verification_status"]
                            for row in corroborated))
        self.assertTrue(all("alone" in row["advice_text"] for row in advice))

    def test_cp011_through_cp020_boss_sequences_are_complete(self):
        expected = {
            "cp_011_la_bravoure": ["Skeleton Squire", "Setesh the Punisher"],
            "cp_013_flying_carpet": ["Sunken Spirits", "Gracos", "King Slime",
                                      "Ethereal Serpent"],
            "cp_015_greenthumb": ["Rainiac"],
            "cp_016_hubble": ["The Envoy", "Hybris"],
            "cp_019_aeolus": ["Vaipur", "Cumulus Vex"],
        }
        for checkpoint_id, subjects in expected.items():
            rows = self.connection.execute(
                """SELECT subject, source_id, locator FROM checkpoint_advice
                WHERE checkpoint_id=? AND advice_type='boss'
                ORDER BY display_order, advice_id""", (checkpoint_id,)
            ).fetchall()
            self.assertEqual([row["subject"] for row in rows], subjects)
            self.assertTrue(all(
                row["source_id"].startswith("game8_boss_")
                or (row["subject"] == "Sunken Spirits"
                    and row["source_id"] == "gamerzenith_green_pillar")
                for row in rows
            ))
            self.assertTrue(all(row["locator"] for row in rows))

    def test_late_game_missing_boss_sequences_are_normalized(self):
        expected = {
            "cp_020_buccanham": ["Togrus Maximus", "The Slamphibians"],
            "cp_021_malign_shrine": ["The Time Being", "Orgodemir first fight"],
            "cp_023_fire_spirit": ["Fire Spirit", "Smothers"],
            "cp_026_elemental_cleanup_nottagen": ["Moostapha", "Malign Vine"],
            "cp_027_deja_vous_rucker": ["Lourgh and Disorder"],
            "cp_030_postgame_another_world": ["The Almighty"],
            "cp_032_yet_another_world": [
                "Xenlon", "The Almighty and Four Spirits", "The Four Spirits"
            ],
        }
        for checkpoint_id, subjects in expected.items():
            rows = self.connection.execute(
                """SELECT subject, source_id, locator, verification_status
                FROM checkpoint_advice
                WHERE checkpoint_id=? AND advice_type='boss'
                ORDER BY display_order, advice_id""", (checkpoint_id,)
            ).fetchall()
            self.assertEqual([row["subject"] for row in rows], subjects)
            self.assertTrue(all(
                row["source_id"].startswith("game8_boss_")
                or (row["subject"] == "Orgodemir first fight"
                    and row["source_id"] == "gamewith_orgodemir_first")
                for row in rows
            ))
            self.assertTrue(all(row["locator"] for row in rows))
            self.assertTrue(all("no_level" in row["verification_status"]
                                or row["subject"] in {
                                    "Orgodemir first fight",
                                    "The Almighty and Four Spirits",
                                    "Togrus Maximus",
                                    "Fire Spirit",
                                    "The Slamphibians",
                                    "Smothers",
                                    "The Four Spirits",
                                } for row in rows))

    def test_medal_tracking_preserves_unknown_and_inconsistent_states(self):
        self.assertEqual(classify_medal_tracking(None, set()), ("unknown", None))
        partial, partial_warning = classify_medal_tracking(None, {1})
        self.assertEqual(partial, "partial")
        self.assertIn("unknown", partial_warning)
        inconsistent, warning = classify_medal_tracking(2, {1})
        self.assertEqual(inconsistent, "inconsistent")
        self.assertIn("disagrees", warning)
        self.assertEqual(classify_medal_tracking(1, {1}), ("known", None))

    def test_walkthrough_cli_defaults_to_saved_checkpoint_or_cp001(self):
        default_state = ROOT / "player" / "ryan-save-state.json"
        self.assertEqual(
            resolve_checkpoint_range(default_state, None, None, None),
            ("cp_001_prologue", "cp_001_prologue"),
        )
        state_path = Path(self.tempdir.name) / "walkthrough-checkpoint-state.json"
        state = json.loads(default_state.read_text())
        state["story"]["checkpoint_id"] = "cp_004_emberdale"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(
            resolve_checkpoint_range(state_path, None, None, None),
            ("cp_004_emberdale", "cp_004_emberdale"),
        )
        self.assertEqual(
            resolve_checkpoint_range(state_path, "cp_005_larca", None, None),
            ("cp_005_larca", "cp_005_larca"),
        )
        self.assertEqual(
            resolve_checkpoint_range(
                state_path, None, "cp_001_prologue", "cp_009_alltrades"
            ),
            ("cp_001_prologue", "cp_009_alltrades"),
        )
        with self.assertRaises(ValueError):
            resolve_checkpoint_range(
                state_path, "cp_005_larca", "cp_001_prologue", "cp_009_alltrades"
            )
        with self.assertRaises(ValueError):
            resolve_checkpoint_range(state_path, None, "cp_001_prologue", None)

    def test_player_progress_records_only_explicit_changes(self):
        state_path = Path(self.tempdir.name) / "explicit-progress.json"
        source = ROOT / "player" / "ryan-save-state.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        update_progress(state_path, self.db_path, "checkpoint", ["cp_004_emberdale"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["story"]["checkpoint_id"], "cp_004_emberdale")
        self.assertEqual(state["completion"]["obligations_completed"], [])

        update_progress(state_path, self.db_path, "medal-found", ["1", "2", "1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["mini_medals_found"], [1, 2])
        update_progress(state_path, self.db_path, "medal-undo", ["1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["mini_medals_found"], [2])
        self.assertIsNone(state["completion"]["mini_medal_count"])
        update_progress(state_path, self.db_path, "medal-count", ["5"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["mini_medal_count"], 5)
        self.assertEqual(state["completion"]["mini_medals_found"], [2])

    def test_accessory_writes_require_owned_verified_quantity_and_reverse(self):
        state_path = Path(self.tempdir.name) / "accessory-progress.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["items_obtained"] = ["item_prayer_ring"]
        state["completion"]["monster_hearts_owned"] = ["heart_slime"]
        state_path.write_text(json.dumps(state), encoding="utf-8")

        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_1", "item_prayer_ring"])
        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_2", "item_slime_heart"])
        recorded = json.loads(state_path.read_text())["party"]["members"]["Hero"]["equipment"]
        self.assertEqual(recorded, {"accessory_1": "item_prayer_ring",
                                    "accessory_2": "item_slime_heart"})

        before_rejection = state_path.read_text()
        for values, message in (
            (["Hero", "accessory_2", "item_prayer_ring"], "explicitly owned copies"),
            (["Hero", "accessory_2", "item_strength_ring"], "not explicitly owned"),
            (["Hero", "accessory_2", "item_cypress_stick"], "does not match"),
        ):
            with self.assertRaisesRegex(ValueError, message):
                update_progress(state_path, self.db_path, "accessory-set", values)
            self.assertEqual(state_path.read_text(), before_rejection)

        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_1", "unknown"])
        recorded = json.loads(state_path.read_text())["party"]["members"]["Hero"]["equipment"]
        self.assertNotIn("accessory_1", recorded)
        self.assertEqual(recorded["accessory_2"], "item_slime_heart")

    def test_explicit_quantities_allow_only_verified_duplicates_and_guard_allocation(self):
        state_path = Path(self.tempdir.name) / "quantity-progress.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state_path.write_text(json.dumps(state), encoding="utf-8")

        update_progress(state_path, self.db_path, "item-obtained",
                        ["item_rabbit_tail"])
        legacy = json.loads(state_path.read_text())
        self.assertNotIn("item_quantities", legacy["completion"])
        update_progress(state_path, self.db_path, "item-quantity",
                        ["item_rabbit_tail", "2"])
        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_1", "item_rabbit_tail"])
        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_2", "item_rabbit_tail"])
        with self.assertRaisesRegex(ValueError, "Not enough explicitly owned copies"):
            update_progress(state_path, self.db_path, "accessory-set",
                            ["Maribel", "accessory_1", "item_rabbit_tail"])
        with self.assertRaisesRegex(ValueError, "reducing quantity below 2"):
            update_progress(state_path, self.db_path, "item-quantity",
                            ["item_rabbit_tail", "1"])

        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_2", "unknown"])
        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_1", "unknown"])
        update_progress(state_path, self.db_path, "item-quantity",
                        ["item_rabbit_tail", "0"])
        saved = json.loads(state_path.read_text())
        self.assertEqual(saved["completion"]["item_quantities"]["item_rabbit_tail"], 0)
        self.assertNotIn("item_rabbit_tail", saved["completion"]["items_obtained"])
        update_progress(state_path, self.db_path, "item-quantity",
                        ["item_rabbit_tail", "unknown"])
        saved = json.loads(state_path.read_text())
        self.assertNotIn("item_rabbit_tail", saved["completion"]["item_quantities"])

        update_progress(state_path, self.db_path, "item-quantity",
                        ["item_prayer_ring", "2"])
        update_progress(state_path, self.db_path, "accessory-set",
                        ["Hero", "accessory_1", "item_prayer_ring"])
        with self.assertRaisesRegex(ValueError, "Duplicate legality is not independently verified"):
            update_progress(state_path, self.db_path, "accessory-set",
                            ["Hero", "accessory_2", "item_prayer_ring"])

    def test_standard_equipment_writes_require_slot_rule_ownership_category_and_compatibility(self):
        state_path = Path(self.tempdir.name) / "equipment-progress.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["items_obtained"] = ["item_cautery_sword", "item_prayer_ring",
                                                   "item_siren_sword"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        update_progress(state_path, self.db_path, "equipment-set",
                        ["Hero", "weapon", "item_cautery_sword"])
        equipment = json.loads(state_path.read_text())["party"]["members"]["Hero"]["equipment"]
        self.assertEqual(equipment["weapon"], "item_cautery_sword")
        before = state_path.read_text()
        for values, message in (
            (["Hero", "shield", "item_cautery_sword"], "does not match"),
            (["Hero", "weapon", "item_cypress_stick"], "not explicitly owned"),
            (["Hero", "weapon", "item_siren_sword"], "Compatibility is not verified"),
            (["Hero", "accessory_1", "item_prayer_ring"], "Unsupported equipment slot"),
        ):
            with self.assertRaisesRegex(ValueError, message):
                update_progress(state_path, self.db_path, "equipment-set", values)
            self.assertEqual(state_path.read_text(), before)
        update_progress(state_path, self.db_path, "equipment-set",
                        ["Hero", "weapon", "unknown"])
        equipment = json.loads(state_path.read_text())["party"]["members"]["Hero"]["equipment"]
        self.assertNotIn("weapon", equipment)

    def test_player_progress_done_is_stable_idempotent_and_reversible(self):
        state_path = Path(self.tempdir.name) / "explicit-done.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(state_path, self.db_path, "done", ["cp_001_prologue", "1"])
        update_progress(state_path, self.db_path, "done", ["cp_001_prologue", "1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(
            state["completion"]["obligations_completed"],
            ["obl_prologue_initial_finite_sweep"],
        )
        report = load_walkthrough(
            self.db_path, state_path, "cp_001_prologue", "cp_001_prologue"
        )
        self.assertEqual([row["display_order"] for row in report["blocks"][0]["now"]], [2])
        update_progress(state_path, self.db_path, "undo", ["cp_001_prologue", "1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["obligations_completed"], [])

    def test_player_progress_rejects_invalid_input_without_writing(self):
        state_path = Path(self.tempdir.name) / "explicit-invalid.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original = state_path.read_text(encoding="utf-8")
        for command, values in (
            ("checkpoint", ["cp_missing"]),
            ("medal-found", ["101"]),
            ("medal-count", ["-1"]),
            ("done", ["cp_001_prologue", "99"]),
        ):
            with self.assertRaises(ValueError):
                update_progress(state_path, self.db_path, command, values)
            self.assertEqual(state_path.read_text(encoding="utf-8"), original)

    def test_walkthrough_distinguishes_cleared_stops_and_unknown_ids(self):
        state_path = Path(self.tempdir.name) / "explicit-stop.json"
        state = json.loads(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8")
        )
        state["completion"]["obligations_completed"] = [
            "obl_prologue_fish_bits", "obsolete_obligation"
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_walkthrough(
            self.db_path, state_path, "cp_001_prologue", "cp_001_prologue"
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report)
        self.assertIn("All recorded warnings cleared", output.getvalue())
        self.assertIn("obsolete_obligation", output.getvalue())
        self.assertIn("completed checks hidden: 1", output.getvalue())

    def test_compact_walkthrough_hides_boilerplate_but_keeps_actions_and_safety(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_003_ballymolloy",
            "cp_003_ballymolloy",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report, compact=True)
        rendered = output.getvalue()
        self.assertNotIn("Chronological walkthrough", rendered)
        self.assertNotIn("No verified STOP recorded", rendered)
        self.assertNotIn("Mark complete:", rendered)
        self.assertNotIn("[complete]", rendered)
        self.assertNotIn("Advice gap:", rendered)
        self.assertIn("NOW:", rendered)
        self.assertIn("SAFE:", rendered)

        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report, compact=True, include_monsters=True)
        self.assertIn("MONSTERS:", output.getvalue())
        self.assertIn("Cactiball", output.getvalue())

    def test_martial_artist_rank_progression_is_complete_and_sourced(self):
        rows = self.connection.execute(
            """SELECT proficiency_rank, skill_name, locator
            FROM vocation_rank_skills WHERE vocation_id='vocation_martial_artist'
            ORDER BY proficiency_rank"""
        ).fetchall()
        self.assertEqual([row[0] for row in rows], list(range(1, 9)))
        self.assertEqual(rows[0][1], "Clap Trap")
        self.assertEqual(rows[-1][1], "Knuckle Sandwich")
        self.assertTrue(all("★" in row[2] for row in rows))
        perk = self.connection.execute(
            """SELECT perk_name FROM vocation_perks
            WHERE vocation_id='vocation_martial_artist' AND perk_type='let_loose'"""
        ).fetchone()
        self.assertEqual(perk[0], "Critical Stance")

    def test_vocation_detail_report_shows_multi_skill_ranks_and_perk(self):
        report = load_vocation_details(self.db_path, "Mage")
        self.assertEqual(report["vocation"]["vocation_id"], "vocation_mage")
        rank_one = [row["skill_name"] for row in report["skills"] if row["proficiency_rank"] == 1]
        self.assertEqual(rank_one, ["Frizz", "Snooze"])
        self.assertEqual(len(report["perks"]), 1)
        output = io.StringIO()
        with redirect_stdout(output):
            print_vocation_details(report)
        self.assertIn("1★ Frizz", output.getvalue())
        self.assertIn("Let Loose:", output.getvalue())

        champion = load_vocation_details(self.db_path, "Champion")
        self.assertEqual(
            [row["prerequisite_name"] for row in champion["requirements"]],
            ["Gladiator", "Paladin"],
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_vocation_details(champion)
        self.assertIn("Unlock: master all — Gladiator, Paladin", output.getvalue())

    def test_all_beginner_vocation_skill_tables_are_complete_and_sourced(self):
        beginner_ids = [
            row[0] for row in self.connection.execute(
                "SELECT vocation_id FROM vocations WHERE tier='beginner'"
            )
        ]
        self.assertEqual(len(beginner_ids), 10)
        for vocation_id in beginner_ids:
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), list(range(1, 9)))
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        same_rank = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_mage' AND proficiency_rank=1
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual([row[0] for row in same_rank], ["Frizz", "Snooze"])

    def test_all_intermediate_vocation_skill_tables_are_complete_and_sourced(self):
        intermediate_ids = [
            row[0] for row in self.connection.execute(
                "SELECT vocation_id FROM vocations WHERE tier='intermediate'"
            )
        ]
        self.assertEqual(len(intermediate_ids), 7)
        for vocation_id in intermediate_ids:
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), list(range(1, 9)))
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        same_rank = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_sage' AND proficiency_rank=1
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in same_rank], ["Insulate", "Midheal", "Squelch"]
        )

    def test_all_advanced_vocation_skill_tables_are_complete_and_sourced(self):
        advanced_ids = [
            row[0] for row in self.connection.execute(
                "SELECT vocation_id FROM vocations WHERE tier='advanced'"
            )
        ]
        self.assertEqual(len(advanced_ids), 3)
        for vocation_id in advanced_ids:
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), list(range(1, 9)))
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        hero_rank_five = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_hero' AND proficiency_rank=5
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual([row[0] for row in hero_rank_five], ["Kazing", "Sword Dance"])

    def test_character_exclusive_vocations_match_direct_sources(self):
        expected = {
            "vocation_fledgling_fisherman": ("Hero", list(range(2, 9))),
            "vocation_heir_apparent": ("Kiefer", list(range(2, 9))),
            "vocation_mini_mayoress": ("Maribel", list(range(2, 9))),
            "vocation_wolf_boy": ("Ruff", list(range(4, 9))),
            "vocation_destinys_dancer": ("Aishe", list(range(1, 9))),
            "vocation_chevalier": ("Sir Mervyn", list(range(1, 9))),
        }
        for vocation_id, (character, ranks) in expected.items():
            vocation = self.connection.execute(
                "SELECT exclusive_character FROM vocations WHERE vocation_id=?",
                (vocation_id,),
            ).fetchone()
            self.assertEqual(vocation[0], character)
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), ranks)
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        destiny_rank_eight = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_destinys_dancer' AND proficiency_rank=8
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in destiny_rank_eight], ["Death Dance", "Kerplunk Dance"]
        )

    def test_vocation_progression_rules_preserve_setting_and_moonlight_scope(self):
        points = {
            (row[0], row[1]): (row[2], row[3])
            for row in self.connection.execute(
                """SELECT event_type, proficiency_setting, proficiency_points,
                    affects_both_moonlight_vocations
                FROM vocation_progression_rules
                WHERE proficiency_points IS NOT NULL"""
            )
        }
        self.assertEqual(points[("overworld_instant_defeat", "Normal")], (1, 1))
        self.assertEqual(points[("battle_completion", "Normal")], (5, 1))
        self.assertEqual(points[("other", "Normal")], (10, 1))
        self.assertEqual(points[("battle_completion", "More")], (7, 1))
        settings = {
            row[0] for row in self.connection.execute(
                """SELECT proficiency_setting FROM vocation_progression_rules
                WHERE event_type='difficulty_setting'"""
            )
        }
        self.assertEqual(settings, {"Less", "Normal", "More"})
        seed_rows = self.connection.execute(
            """SELECT rank_delta, affects_both_moonlight_vocations, locator
            FROM vocation_progression_rules
            WHERE event_type='proficiency_seed'
            ORDER BY affects_both_moonlight_vocations"""
        ).fetchall()
        self.assertEqual([(row[0], row[1]) for row in seed_rows], [(1, 0), (1, 1)])
        self.assertTrue(all(row[2].strip() for row in seed_rows))
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM vocation_progression_rules"
            ).fetchone()[0],
            9,
        )

    def test_luminary_rank_costs_are_two_source_verified(self):
        rows = self.connection.execute(
            """SELECT proficiency_rank, proficiency_points, cumulative_points,
                source_id, corroborating_source_id, verification_status
            FROM vocation_rank_costs
            WHERE vocation_id='vocation_luminary'
            ORDER BY proficiency_rank"""
        ).fetchall()
        self.assertEqual(
            [(row[0], row[1], row[2]) for row in rows],
            [(2, 25, 25), (3, 35, 60), (4, 40, 100), (5, 65, 165),
             (6, 75, 240), (7, 110, 350), (8, 130, 480)],
        )
        self.assertTrue(all(row[3] != row[4] for row in rows))
        self.assertTrue(all(row[5] == "two_independent_current_version_tables_match" for row in rows))

    def test_numeric_vocation_rank_costs_are_cell_level_corroborated(self):
        rows = self.connection.execute(
            """SELECT vocation_id, proficiency_rank, proficiency_points,
                cumulative_points, source_id, corroborating_source_id,
                locator, corroborating_locator, verification_status
            FROM vocation_rank_costs ORDER BY vocation_id, proficiency_rank"""
        ).fetchall()
        self.assertEqual(len(rows), 163)
        self.assertEqual(len({row[0] for row in rows}), 24)
        self.assertTrue(all(row[1] in range(2, 9) and row[2] > 0 for row in rows))
        self.assertTrue(all(row[4] != row[5] for row in rows))
        self.assertTrue(all(row[6].strip() and row[7].strip() for row in rows))
        self.assertTrue(all(row[8].startswith(
            "two_independent_current_version_tables_match") for row in rows))
        for vocation_id in {row[0] for row in rows}:
            ladder = [row for row in rows if row[0] == vocation_id]
            expected_ranks = [7, 8] if vocation_id == "vocation_wolf_boy" else list(range(2, 9))
            self.assertEqual([row[1] for row in ladder], expected_ranks)
            cumulative = 0
            for row in ladder:
                cumulative += row[2]
                self.assertEqual(row[3], cumulative)

    def test_all_vocations_have_two_source_progression_profiles(self):
        rows = self.connection.execute(
            """SELECT vocation_id, progression_mode, normalized_total_points,
                first_numeric_rank, last_numeric_rank, source_id,
                corroborating_source_id, verification_status
            FROM vocation_progression_profiles ORDER BY vocation_id"""
        ).fetchall()
        self.assertEqual(len(rows), 26)
        self.assertTrue(all(row[5] != row[6] for row in rows))
        self.assertTrue(all(
            row[7] == "two_independent_current_version_progression_tables"
            for row in rows
        ))
        profiles = {row[0]: tuple(row[1:5]) for row in rows}
        self.assertEqual(profiles["vocation_wolf_boy"],
                         ("story_then_points", 150, 7, 8))
        self.assertEqual(profiles["vocation_destinys_dancer"],
                         ("story_granted", 0, None, None))
        self.assertEqual(profiles["vocation_chevalier"],
                         ("story_granted", 0, None, None))
        full = [row for row in rows if row[1] == "full_points"]
        self.assertEqual(len(full), 23)
        self.assertTrue(all(row[3:5] == (2, 8) for row in full))
        conflicts = self.connection.execute(
            """SELECT status, detection_method FROM conflicts
            WHERE conflict_key LIKE '%|vocation_rank_progression|%'"""
        ).fetchall()
        self.assertEqual(len(conflicts), 6)
        self.assertTrue(all(tuple(row) == (
            "resolved", "two_source_personal_vocation_adjudication"
        ) for row in conflicts))

    def test_numeric_stat_cells_separate_matches_from_conflicts(self):
        verified = self.connection.execute(
            """SELECT modifier_value, modifier_unit, source_id,
                corroborating_source_id, locator, corroborating_locator,
                confidence, verification_status
            FROM vocation_stat_modifiers WHERE modifier_value IS NOT NULL"""
        ).fetchall()
        self.assertEqual(len(verified), 234)
        self.assertTrue(all(row[1] == "percent" for row in verified))
        self.assertTrue(all(row[2] == "dqst_vocation_tables" for row in verified))
        self.assertTrue(all(row[3] == "hyperwiki_vocation_stats" for row in verified))
        self.assertTrue(all(row[4].strip() and row[5].strip() for row in verified))
        self.assertTrue(all(row[6] == "verified" for row in verified))
        self.assertTrue(all(
            row[7] == "two_independent_current_version_cells_match_dqst_hyperwiki"
            for row in verified
        ))
        stat_conflicts = self.connection.execute(
            """SELECT COUNT(*) FROM conflicts
            WHERE conflict_key LIKE '%|numeric_stat_modifier_%' AND status='resolved'
              AND detection_method='third_source_cell_level_adjudication'"""
        ).fetchone()[0]
        self.assertEqual(stat_conflicts, 72)
        unresolved_stats = self.connection.execute(
            """SELECT COUNT(*) FROM conflicts
            WHERE conflict_key LIKE '%|numeric_stat_modifier_%' AND status='unresolved'"""
        ).fetchone()[0]
        self.assertEqual(unresolved_stats, 0)
        jester_total = self.connection.execute(
            """SELECT COUNT(*) FROM conflicts
            WHERE conflict_key LIKE 'vocation:jester|numeric_mastery_total|%'
              AND status='resolved'
              AND detection_method='third_source_rank_cells_and_arithmetic'"""
        ).fetchone()[0]
        self.assertEqual(jester_total, 1)
        luminary_aggregate = self.connection.execute(
            """SELECT status, detection_method FROM conflicts
            WHERE (claim_a_id='claim_luminary_numeric_modifiers_dqst'
                   AND claim_b_id='claim_luminary_numeric_modifiers_dqorg')
               OR (claim_a_id='claim_luminary_numeric_modifiers_dqorg'
                   AND claim_b_id='claim_luminary_numeric_modifiers_dqst')"""
        ).fetchone()
        self.assertEqual(tuple(luminary_aggregate),
                         ("resolved", "third_source_complete_row_adjudication"))

    def test_lucky_panel_attempt_rule_has_two_source_free_entry(self):
        row = self.connection.execute(
            """SELECT max_attempts_per_day, reset_action, entry_cost, currency,
                source_id, corroborating_source_id, verification_status
            FROM lucky_panel_rules WHERE rule_id='lprule_daily_attempts'"""
        ).fetchone()
        self.assertEqual((row[0], row[1]), (3, "Stay at an inn"))
        self.assertEqual(row[2], 0)
        self.assertIsNone(row[3])
        self.assertNotEqual(row[4], row[5])
        self.assertIn("match_free_entry", row[6])

    def test_lucky_panel_numeric_cells_are_not_probabilities(self):
        row = self.connection.execute(
            """SELECT value_json, claim_kind, confidence, verification_status
            FROM claims WHERE claim_id='claim_lucky_panel_numeric_cells'"""
        ).fetchone()
        value = json.loads(row[0])
        self.assertEqual(row[1], "unknown")
        self.assertEqual(row[2], "medium")
        self.assertIsNone(value["probability_formula"])
        self.assertIsNone(value["normalized_probabilities"])
        self.assertIn("not standalone item probabilities", value["safe_interpretation"])

    def test_moonlighting_sequence_and_skill_scope_are_resolved(self):
        conflict = self.connection.execute(
            """SELECT status, rationale FROM conflicts
            WHERE claim_a_id='claim_moonlighting_unlock'
              AND claim_b_id='claim_moonlighting_unlock_rpgsite'"""
        ).fetchone()
        self.assertEqual(conflict[0], "resolved")
        self.assertIn("process-stage", conflict[1])
        sequence = self.connection.execute(
            """SELECT value_json, confidence FROM claims
            WHERE claim_id='claim_moonlighting_sequence_corroborated'"""
        ).fetchone()
        self.assertIn('"trigger_location": "Shrine of Mysteries"', sequence[0])
        self.assertIn('"activation_location": "Alltrades Abbey"', sequence[0])
        self.assertEqual(sequence[1], "verified")
        retention = self.connection.execute(
            """SELECT value_json FROM claims
            WHERE claim_id='claim_vocation_skill_retention'"""
        ).fetchone()[0]
        self.assertIn('"retained_after_switching": false', retention)
        pairing_rows = self.connection.execute(
            """SELECT claim_id, value_json, source_id, confidence
            FROM claims WHERE predicate='legal_pairing_rule'
            ORDER BY claim_id"""
        ).fetchall()
        self.assertEqual(len(pairing_rows), 2)
        self.assertEqual({row[2] for row in pairing_rows}, {
            "playstation_blog_dq7r_interview", "xbox_wire_dq7r_tips",
        })
        self.assertTrue(all(row[3] == "verified" for row in pairing_rows))
        playstation = next(row[1] for row in pairing_rows
                           if row[2] == "playstation_blog_dq7r_interview")
        xbox = next(row[1] for row in pairing_rows
                    if row[2] == "xbox_wire_dq7r_tips")
        self.assertIn('"Intermediate + Intermediate"', playstation)
        self.assertIn('"distinct_vocations_required": true', xbox)

    def test_magic_shield_numeric_stats_have_two_source_agreement(self):
        expected = {
            "defence_bonus": 22,
            "magical_might_bonus": 12,
            "magical_mending_bonus": 11,
            "elemental_damage_reduction_percent": 5,
        }
        rows = self.connection.execute(
            """SELECT predicate, value_json, source_id, confidence,
                verification_status
            FROM claims
            WHERE subject_key='item:magic_shield'
              AND predicate IN ('defence_bonus', 'magical_might_bonus',
                'magical_mending_bonus', 'elemental_damage_reduction_percent')
            ORDER BY predicate, source_id"""
        ).fetchall()
        self.assertEqual(len(rows), 8)
        for predicate, value in expected.items():
            matching = [row for row in rows if row[0] == predicate]
            self.assertEqual(len(matching), 2)
            self.assertEqual({json.loads(row[1]) for row in matching}, {value})
            self.assertEqual(len({row[2] for row in matching}), 2)
            self.assertTrue(all(row[3] == "verified" for row in matching))
            self.assertTrue(all(
                row[4] == "two_independent_current_version_sources"
                for row in matching
            ))

    def test_mighty_pip_control_advice_is_corroborated_and_rank_gated(self):
        rows = self.connection.execute(
            """SELECT value_json, source_id, claim_kind, confidence
            FROM claims
            WHERE subject_key='boss:the_mighty_pip'
              AND predicate='recommended_control_tool'
            ORDER BY source_id, claim_id"""
        ).fetchall()
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row[1] for row in rows}), 2)
        self.assertTrue(all(row[2] == "recommendation" for row in rows))
        self.assertTrue(all(row[3] == "verified" for row in rows))
        values = [json.loads(row[0]) for row in rows]
        for skill in ("Leg Sweep", "Dazzle"):
            matching = [value for value in values if value["skill"] == skill]
            self.assertEqual(len(matching), 2)
            self.assertTrue(all("proficiency_rank" not in value for value in matching))
        self.assertEqual(
            {value["boss_resistance"] for value in values
             if value["skill"] == "Dazzle"},
            {"resisted"},
        )
        advice = self.connection.execute(
            """SELECT advice_text, applicability_json, confidence
            FROM checkpoint_advice WHERE advice_id='advice_cp010_mighty_pip'"""
        ).fetchone()
        applicability = json.loads(advice[1])
        self.assertEqual(applicability["skill_gates"]["Leg Sweep"]["proficiency_rank"], 2)
        self.assertEqual(applicability["skill_gates"]["Dazzle"]["proficiency_rank"], 2)
        self.assertIn("resists", advice[0])
        self.assertEqual(advice[2], "high")
        structured = self.connection.execute(
            """SELECT b.recommendation_verification_status,
                b.corroborating_source_id, k.proficiency_rank,
                k.verification_status
            FROM boss_skill_recommendations b
            JOIN vocation_rank_skills k USING(vocation_skill_id)
            WHERE b.boss_name='The Mighty Pip'
              AND k.skill_name IN ('Leg Sweep', 'Dazzle')
            ORDER BY k.skill_name"""
        ).fetchall()
        self.assertEqual(len(structured), 2)
        self.assertTrue(all(row[0] == "two_source_verified" for row in structured))
        self.assertEqual({row[1] for row in structured}, {"gamewith_mighty_pip"})
        self.assertEqual({row[2] for row in structured}, {2})
        self.assertTrue(all(not row[3].startswith("two_") for row in structured))

    def test_alltrades_arena_vocation_components_are_independently_attributed(self):
        expected = {
            ("character:hero", "Warrior"),
            ("character:maribel", "Mage"),
            ("character:ruff", "Priest"),
        }
        for subject_key, vocation in expected:
            rows = self.connection.execute(
                """SELECT value_json, source_id, claim_kind, confidence,
                    verification_status
                FROM claims
                WHERE subject_key=? AND predicate='recommended_early_vocation'
                  AND json_extract(value_json, '$')=?
                ORDER BY source_id""",
                (subject_key, vocation),
            ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({row[1] for row in rows}), 2)
            self.assertTrue(all(row[2] == "recommendation" for row in rows))
            self.assertTrue(all(row[3] == "verified" for row in rows))
            self.assertTrue(all("editorial" in row[4] for row in rows))

        advice = self.connection.execute(
            """SELECT applicability_json, verification_status
            FROM checkpoint_advice
            WHERE advice_id='advice_cp009_vocations_arena_power'"""
        ).fetchone()
        applicability = json.loads(advice[0])
        self.assertEqual(set(applicability["component_corroboration"]), {
            "Hero Warrior", "Maribel Mage", "Ruff Priest",
        })
        self.assertEqual(
            advice[1],
            "componentwise_two_source_editorial_exact_trio_single_source",
        )
        self.assertIn("only Game8", applicability["evidence_note"])

    def test_alltrades_boss_core_tactics_preserve_source_strength(self):
        verified = {
            "recommended_burst_response": 2,
            "first_encounter_outcome": 2,
            "rematch_recovery_method": 2,
        }
        for predicate, expected_count in verified.items():
            rows = self.connection.execute(
                """SELECT source_id, confidence, verification_status
                FROM claims WHERE predicate=?
                  AND subject_key IN ('boss:cardinal_sin',
                                      'boss:rashers_and_stripes')
                ORDER BY source_id""",
                (predicate,),
            ).fetchall()
            self.assertEqual(len(rows), expected_count)
            self.assertEqual(len({row[0] for row in rows}), expected_count)
            self.assertTrue(all(row[1] == "verified" for row in rows))
            self.assertTrue(
                all(row[2] == "two_independent_current_version_sources" for row in rows)
            )

        single = self.connection.execute(
            """SELECT confidence, verification_status FROM claims
            WHERE subject_key='boss:rashers_and_stripes'
              AND predicate='recommended_target_priority'"""
        ).fetchone()
        self.assertEqual(tuple(single), ("high", "single_independent_source"))

        advice = self.connection.execute(
            """SELECT advice_text, verification_status FROM checkpoint_advice
            WHERE advice_id='advice_cp009_rashers_stripes'"""
        ).fetchone()
        self.assertIn("single-source target order", advice[0])
        self.assertIn("two_independent_sources", advice[1])

    def test_early_recommended_gear_stats_have_two_source_agreement(self):
        expected = {
            "item:snooze_stick": {"attack_bonus": 18, "magical_might_bonus": 22,
                "magical_mending_bonus": 12, "mp_absorption_percent": 8,
                "battle_use_effect": "Attempts to put one enemy to sleep"},
            "item:iron_mask": {"defence_bonus": 25},
            "item:windcheater": {"defence_bonus": 33, "deftness_bonus": 50,
                "drop_rate_effect": "Enemies are more likely to drop items"},
            "item:white_shield": {"defence_bonus": 19,
                "block_chance_percent": 6, "fire_damage_reduction_percent": 10},
        }
        for subject, predicates in expected.items():
            for predicate, expected_value in predicates.items():
                rows = self.connection.execute(
                    "SELECT value_json, source_id, confidence FROM claims "
                    "WHERE subject_key=? AND predicate=?", (subject, predicate)
                ).fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual({json.loads(row[0]) for row in rows}, {expected_value})
                self.assertEqual(len({row[1] for row in rows}), 2)
                self.assertTrue(all(row[2] == "verified" for row in rows))

    def test_advanced_vocation_stat_modifiers_are_complete_and_qualitative(self):
        for vocation_id in ("vocation_champion", "vocation_druid", "vocation_hero"):
            rows = self.connection.execute(
                """SELECT stat_key, modifier_direction, modifier_value,
                    proficiency_rank, locator, source_id
                FROM vocation_stat_modifiers
                WHERE vocation_id=? AND modifier_value IS NULL""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(len(rows), 11)
            self.assertEqual(len({row[0] for row in rows}), 11)
            self.assertTrue(all(row[1] in {"increased", "normal", "decreased"} for row in rows))
            self.assertTrue(all(row[2] is None and row[3] is None for row in rows))
            self.assertTrue(all("Overview > Stat Bonuses >" in row[4] for row in rows))
            self.assertTrue(all(row[5].startswith("game8_vocation_") for row in rows))

        champion_resilience = self.connection.execute(
            """SELECT modifier_direction FROM vocation_stat_modifiers
            WHERE vocation_id='vocation_champion' AND stat_key='resilience'
              AND modifier_value IS NULL"""
        ).fetchone()[0]
        self.assertEqual(champion_resilience, "normal")

    def test_beginner_and_intermediate_stat_modifiers_are_complete(self):
        vocation_ids = [
            row[0] for row in self.connection.execute(
                """SELECT vocation_id FROM vocations
                WHERE tier IN ('beginner', 'intermediate')"""
            )
        ]
        self.assertEqual(len(vocation_ids), 17)
        for vocation_id in vocation_ids:
            rows = self.connection.execute(
                """SELECT stat_key, modifier_direction, modifier_value,
                    proficiency_rank, locator, source_id
                FROM vocation_stat_modifiers
                WHERE vocation_id=? AND modifier_value IS NULL""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(len(rows), 11)
            self.assertEqual(len({row[0] for row in rows}), 11)
            self.assertTrue(all(row[1] in {"increased", "normal", "decreased"} for row in rows))
            self.assertTrue(all(row[2] is None and row[3] is None for row in rows))
            self.assertTrue(all("Overview > Stat Bonuses >" in row[4] for row in rows))
            self.assertTrue(all(row[5].startswith("game8_vocation_") for row in rows))

        shepherd = dict(
            self.connection.execute(
                """SELECT stat_key, modifier_direction FROM vocation_stat_modifiers
                WHERE vocation_id='vocation_shepherd' AND modifier_value IS NULL"""
            ).fetchall()
        )
        self.assertEqual(shepherd["max_hp"], "increased")
        self.assertEqual(shepherd["attack"], "decreased")
        self.assertEqual(shepherd["agility"], "decreased")

    def test_cp010_through_cp019_two_source_advice_has_atomic_evidence_links(self):
        expected = {
            "advice_cp010_mild_bunch", "advice_cp010_mighty_pip",
            "advice_cp011_skeleton_squire", "advice_cp011_setesh",
            "advice_cp013_sunken_spirits", "advice_cp013_king_slime",
            "advice_cp013_ethereal_serpent", "advice_cp013_gracos",
            "advice_cp014_gracos_v", "advice_cp016_envoy",
            "advice_cp016_advanced_path_routing",
            "advice_cp017_gladiator_burst", "advice_cp018_gasputin",
            "advice_cp019_vaipur", "advice_cp019_cumulus_vex",
        }
        rows = self.connection.execute(
            """SELECT advice_id, applicability_json FROM checkpoint_advice
            WHERE checkpoint_id BETWEEN 'cp_010_alltrades_present'
                AND 'cp_019_aeolus'"""
        ).fetchall()
        linked = {}
        for row in rows:
            if row[0] not in expected:
                continue
            claim_ids = json.loads(row[1]).get("evidence_claim_ids", [])
            self.assertGreaterEqual(len(claim_ids), 2, row[0])
            placeholders = ",".join("?" for _ in claim_ids)
            claims = self.connection.execute(
                f"SELECT claim_id, source_id FROM claims "
                f"WHERE claim_id IN ({placeholders})", claim_ids
            ).fetchall()
            self.assertEqual(len(claims), len(set(claim_ids)), row[0])
            self.assertGreaterEqual(len({claim[1] for claim in claims}), 2, row[0])
            linked[row[0]] = set(claim_ids)
        self.assertEqual(set(linked), expected)
        self.assertNotIn("claim_gasputin_item_fallback_game8",
                         linked["advice_cp018_gasputin"])
        self.assertNotIn("claim_gracos_dazzle_game8",
                         linked["advice_cp013_gracos"])
        self.assertNotIn("claim_cumulus_vex_wind_resistance_game8",
                         linked["advice_cp019_cumulus_vex"])


if __name__ == "__main__":
    unittest.main()
