"""Verify the real compiled publisher template, without Azure credentials."""

import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "infra" / "bicep" / "owned-publisher.bicep"


def assert_contract(case, template):
    resources = template["resources"]
    case.assertEqual(len(resources), 1, "Only the new pool may be deployed")
    pool = resources[0]
    case.assertEqual(
        pool["type"], "Microsoft.ContainerRegistry/registries/agentPools"
    )
    case.assertEqual(pool["apiVersion"], "2025-03-01-preview")
    case.assertEqual(pool["location"], "[parameters('location')]")
    case.assertEqual(
        pool["properties"],
        {
            "count": "[parameters('capacity')]",
            "os": "Linux",
            "tier": "S1",
            "virtualNetworkSubnetResourceId": "[parameters('buildSubnetResourceId')]",
        },
    )
    case.assertNotIn("identity", pool)
    parameters = template["parameters"]
    case.assertEqual(parameters["capacity"]["defaultValue"], 0)
    case.assertEqual(parameters["capacity"]["allowedValues"], [0, 1])
    case.assertEqual(parameters["location"]["allowedValues"], ["swedencentral"])
    case.assertNotIn("defaultValue", parameters["buildSubnetResourceId"])
    case.assertEqual(parameters["buildSubnetResourceId"]["minLength"], 1)
    case.assertNotIn("defaultValue", parameters["registryName"])
    case.assertNotIn("defaultValue", parameters["agentPoolName"])
    case.assertEqual(
        set(template["outputs"]), {"agentPoolResourceId"}
    )


class OwnedPublisherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable = shutil.which("bicep")
        if not executable:
            raise RuntimeError("Bicep CLI is required; contract tests never skip.")
        result = subprocess.run(
            [executable, "build", str(TEMPLATE), "--stdout"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.stderr.strip():
            raise AssertionError(f"Bicep emitted diagnostics: {result.stderr}")
        cls.compiled = json.loads(result.stdout)

    def test_real_compiled_template_has_pool_only(self):
        assert_contract(self, self.compiled)

    def test_public_registry_redeployment_is_detected(self):
        mutated = copy.deepcopy(self.compiled)
        mutated["resources"].append(
            {
                "type": "Microsoft.ContainerRegistry/registries",
                "properties": {
                    "publicNetworkAccess": "Enabled",
                    "adminUserEnabled": True,
                },
            }
        )
        with self.assertRaisesRegex(AssertionError, "Only the new pool"):
            assert_contract(self, mutated)

    def test_removing_private_subnet_is_detected(self):
        mutated = copy.deepcopy(self.compiled)
        del mutated["resources"][0]["properties"]["virtualNetworkSubnetResourceId"]
        with self.assertRaises(AssertionError):
            assert_contract(self, mutated)

    def test_unbounded_capacity_is_detected(self):
        mutated = copy.deepcopy(self.compiled)
        mutated["parameters"]["capacity"]["allowedValues"].append(2)
        with self.assertRaises(AssertionError):
            assert_contract(self, mutated)

    def test_standing_capacity_is_detected(self):
        mutated = copy.deepcopy(self.compiled)
        mutated["parameters"]["capacity"]["defaultValue"] = 1
        with self.assertRaises(AssertionError):
            assert_contract(self, mutated)

    def test_expensive_tier_is_detected(self):
        mutated = copy.deepcopy(self.compiled)
        mutated["resources"][0]["properties"]["tier"] = "I6"
        with self.assertRaises(AssertionError):
            assert_contract(self, mutated)

    def test_invented_idle_timeout_is_detected(self):
        mutated = copy.deepcopy(self.compiled)
        mutated["resources"][0]["properties"]["idleTimeout"] = 60
        with self.assertRaises(AssertionError):
            assert_contract(self, mutated)

    def test_identity_grant_is_detected(self):
        mutated = copy.deepcopy(self.compiled)
        mutated["resources"][0]["identity"] = {"type": "SystemAssigned"}
        with self.assertRaises(AssertionError):
            assert_contract(self, mutated)


if __name__ == "__main__":
    unittest.main()
