name: Verify Money Factory Legal Aid v1.668

on:
  push:
    branches: [ main ]
    paths:
      - 'money_factory_legal_aid_v1_668/**'
  pull_request:
    branches: [ main ]

jobs:
  verify-architecture:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout DashandSeal/Sanders_Dash_Seal
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Native Build Tools & Dependencies
        run: |
          sudo apt-get update && sudo apt-get install -y cmake gcc g++ ninja-build libssl-dev
          pip install -r money_factory_legal_aid_v1_668/requirements.txt

      - name: Run Hard-Lock & ML-DSA-65 Lattice Smoke Test
        working-directory: money_factory_legal_aid_v1_668
        run: |
          python3 -c '
          from shield.sovereign_shield_v3 import SovereignShieldV3
          s = SovereignShieldV3("CI-VERIFY-01", "US-CO-COS")
          coc = s.generate_lattice_coc({"case": "ci_verify"}, "a"*64, "541110")
          assert coc["court_admissibility_status"] == "VERIFIED_IMMUTABLE_2026"
          print("VERIFIED:", coc["pqc_algorithm"], coc["court_admissibility_status"])
          '
