import unittest
from backend.rules import anomaly_rules as rules

class HealthTests(unittest.TestCase):
    def test_empty_is_unknown(self):
        for state in [None, {}, {"values":{}}, {"values":None}]:
            self.assertEqual(rules.evaluate_health(state)["health"], "UNKNOWN")
    def test_temperature_boundaries(self):
        for temperature, expected in [(rules.TEMP_WARN-1,"OK"),(rules.TEMP_WARN,"WARNING"),(rules.TEMP_CRIT,"CRITICAL")]:
            self.assertEqual(rules.evaluate_health({"values":{"temperature":temperature}})["health"], expected)
    def test_critical_takes_precedence(self):
        result=rules.evaluate_health({"values":{"temperature":rules.TEMP_CRIT,"vibration":rules.VIB_WARN}})
        self.assertEqual(result["health"], "CRITICAL")
        self.assertEqual(len(result["alerts"]), 2)
    def test_low_speed_only_warns_while_running(self):
        for status, expected in [("stopped","OK"),("running","WARNING")]:
            self.assertEqual(rules.evaluate_health({"values":{"status":status,"beltSpeed":0,"sawRpm":0}})["health"], expected)
