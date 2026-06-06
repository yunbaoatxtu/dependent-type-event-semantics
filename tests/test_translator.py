import json
import unittest
from pathlib import Path

from translator.dependent_type_event_translator import check_term, translate


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "translator" / "examples"


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


class TranslatorTests(unittest.TestCase):
    def test_variable_polyadicity_and_time(self) -> None:
        result = translate(load_example("example_butter.json"))
        self.assertEqual(result["adverb_count"], 2)
        self.assertEqual(
            result["translation"],
            "at_T(noon, butter(2)(slowly, in(bathroom), John, toast))",
        )
        self.assertEqual(result["ast"]["kind"], "time")
        self.assertEqual(result["ast"]["body"]["kind"], "application")
        self.assertEqual(result["ast"]["body"]["modifiers"], ["slowly", "in(bathroom)"])
        self.assertEqual(result["type_check"], {"ok": True, "type": "t", "errors": []})
        self.assertEqual(result["residual_atoms_not_translated"], [])

    def test_argument_omission_introduces_sigma_witness(self) -> None:
        result = translate(load_example("example_eat_omission.json"))
        self.assertEqual(
            result["translation"],
            "Sigma x_theme : Food. eat(0)(John, x_theme)",
        )
        self.assertEqual(
            result["omitted_arguments"],
            [{"role": "Theme", "witness": "x_theme", "type": "Food"}],
        )
        self.assertEqual(result["ast"]["kind"], "sigma")
        self.assertEqual(result["ast"]["body"]["kind"], "application")
        self.assertEqual(result["ast"]["body"]["arguments"], ["John", "x_theme"])
        self.assertTrue(result["type_check"]["ok"])

    def test_event_counting_wraps_proposition(self) -> None:
        result = translate(load_example("example_knock_twice.json"))
        self.assertEqual(result["counts"], ["2"])
        self.assertEqual(result["translation"], "repeat(2, knock(0)(John))")
        self.assertEqual(result["ast"]["kind"], "repeat")
        self.assertEqual(result["ast"]["body"]["function"], "knock")
        self.assertTrue(result["type_check"]["ok"])

    def test_resultative_becomes_causal_transition(self) -> None:
        result = translate(load_example("example_break_result.json"))
        self.assertEqual(result["result_states"], ["broken"])
        self.assertEqual(
            result["translation"],
            "Cause(John, Transition(vase, _, broken))",
        )
        self.assertEqual(result["ast"]["kind"], "cause")
        self.assertEqual(result["ast"]["effect"]["kind"], "transition")
        self.assertEqual(result["ast"]["activity"]["function"], "break")
        self.assertTrue(result["type_check"]["ok"])

    def test_type_checker_rejects_bad_adverb_count(self) -> None:
        result = check_term(
            {
                "kind": "application",
                "function": "butter",
                "adverb_count": 1,
                "modifiers": ["slowly", "carefully"],
                "arguments": ["John", "toast"],
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("does not match", result["errors"][0])

    def test_type_checker_rejects_bad_cause_effect(self) -> None:
        result = check_term(
            {
                "kind": "cause",
                "causer": "John",
                "effect": {
                    "kind": "application",
                    "function": "break",
                    "adverb_count": 0,
                    "modifiers": [],
                    "arguments": ["John", "vase"],
                },
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("cause.effect must have type Transition", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
