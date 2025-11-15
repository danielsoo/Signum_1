#!/usr/bin/env python3
"""Test SIGNUM imports"""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
provider_path = project_root / "provider"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(provider_path))

print("🔍 Testing SIGNUM imports...")
print(f"📁 Project root: {project_root}")
print(f"📁 Provider path: {provider_path}")
print(f"🐍 Python: {sys.executable}")

success_count = 0
fail_count = 0

# Test 1: Hospital modules
print("\n1️⃣ Testing hospital modules...")
try:
    from provider.hospital import UnifiedHospitalService
    print("   ✅ UnifiedHospitalService")
    success_count += 1
except Exception as e:
    print(f"   ❌ UnifiedHospitalService: {e}")
    fail_count += 1

try:
    from provider.hospital import HospitalSearchEngine
    print("   ✅ HospitalSearchEngine")
    success_count += 1
except Exception as e:
    print(f"   ❌ HospitalSearchEngine: {e}")
    fail_count += 1

try:
    from provider.hospital import RiskAnalyzer
    print("   ✅ RiskAnalyzer")
    success_count += 1
except Exception as e:
    print(f"   ❌ RiskAnalyzer: {e}")
    fail_count += 1

# Test 2: Government modules
print("\n2️⃣ Testing government modules...")
try:
    from provider.government.clients_free import NPPESClient
    print("   ✅ NPPESClient")
    success_count += 1
except Exception as e:
    print(f"   ❌ NPPESClient: {e}")
    fail_count += 1

# Test 3: Google modules
print("\n3️⃣ Testing Google modules...")
try:
    from provider.google.places_client_v1 import PlacesV1Client
    print("   ✅ PlacesV1Client")
    success_count += 1
except Exception as e:
    print(f"   ❌ PlacesV1Client: {e}")
    fail_count += 1

# Test 4: Interactive search
print("\n4️⃣ Testing interactive search...")
try:
    import provider.hospital.interactive_search as interactive_search
    print("   ✅ interactive_search module")
    success_count += 1
except Exception as e:
    print(f"   ❌ interactive_search: {e}")
    fail_count += 1

# Test 5: Try to initialize services
print("\n5️⃣ Testing service initialization...")
warehouse_dir = project_root / "provider" / "hospital" / "warehouse"
warehouse_dir.mkdir(parents=True, exist_ok=True)

try:
    from provider.hospital import HospitalSearchEngine
    search_engine = HospitalSearchEngine(str(warehouse_dir))
    print(f"   ✅ HospitalSearchEngine initialized")
    success_count += 1
except Exception as e:
    print(f"   ❌ HospitalSearchEngine init: {e}")
    fail_count += 1

try:
    from provider.government.clients_free import NPPESClient
    nppes = NPPESClient()
    print(f"   ✅ NPPESClient initialized")
    success_count += 1
except Exception as e:
    print(f"   ❌ NPPESClient init: {e}")
    fail_count += 1

# Summary
print("\n" + "="*50)
print(f"📊 Results: {success_count} passed, {fail_count} failed")
if fail_count == 0:
    print("🎉 All tests passed!")
else:
    print("⚠️  Some tests failed")
print("="*50)
