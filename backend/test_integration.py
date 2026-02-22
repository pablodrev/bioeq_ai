"""
Simple test script to verify all imports and basic functionality.
Run: python test_integration.py
"""

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from database import init_db, SessionLocal, Base
        print("✓ database.py")
    except Exception as e:
        print(f"✗ database.py: {e}")
        return False
    
    try:
        from models import DBProject, DBDrugParameter
        print("✓ models.py")
    except Exception as e:
        print(f"✗ models.py: {e}")
        return False
    
    try:
        from schemas import SearchStartRequest, SearchResultsResponse
        print("✓ schemas.py")
    except Exception as e:
        print(f"✗ schemas.py: {e}")
        return False
    
    try:
        from services.pubmed import PubMedClient
        print("✓ services/pubmed.py")
    except Exception as e:
        print(f"✗ services/pubmed.py: {e}")
        return False
    
    try:
        from services.llm_client import YandexGPTClient
        print("✓ services/llm_client.py")
    except Exception as e:
        print(f"✗ services/llm_client.py: {e}")
        return False
    
    try:
        from services.calculator import BioeEquivalenceCalculator
        print("✓ services/calculator.py")
    except Exception as e:
        print(f"✗ services/calculator.py: {e}")
        return False
    
    try:
        from core.parsing_module import ParsingModule
        print("✓ core/parsing_module.py")
    except Exception as e:
        print(f"✗ core/parsing_module.py: {e}")
        return False
    
    try:
        from core.design_module import DesignModule
        print("✓ core/design_module.py")
    except Exception as e:
        print(f"✗ core/design_module.py: {e}")
        return False
    
    try:
        from core.regulatory_module import RegulatoryModule
        print("✓ core/regulatory_module.py")
    except Exception as e:
        print(f"✗ core/regulatory_module.py: {e}")
        return False
    
    try:
        from core.report_module import ReportModule
        print("✓ core/report_module.py")
    except Exception as e:
        print(f"✗ core/report_module.py: {e}")
        return False
    
    try:
        import main
        print("✓ main.py (FastAPI app)")
    except Exception as e:
        print(f"✗ main.py: {e}")
        return False
    
    return True


def test_calculator():
    """Test sample size calculation."""
    print("\nTesting calculator...")
    
    from services.calculator import BioeEquivalenceCalculator
    
    calc = BioeEquivalenceCalculator()
    
    # Test case: CV_intra = 22.5% (common value)
    n, design = calc.calculate_sample_size(cv_intra=22.5, power=0.80)
    
    print(f"  CV_intra: 22.5%")
    print(f"  Sample size (N): {n}")
    print(f"  Design: {design}")
    
    assert n > 0, "Sample size should be positive"
    assert design == "2x2 crossover", "Default design should be 2x2 crossover"
    
    # Test washout
    washout = calc.estimate_washout_period(t_half=2.1)
    print(f"  T1/2: 2.1 hours → Washout: {washout} days")
    
    assert washout > 0, "Washout should be positive"
    
    print("✓ Calculator works correctly")
    return True


def test_database_models():
    """Test database models."""
    print("\nTesting database models...")
    
    from database import Base
    from models import DBProject, DBDrugParameter
    
    # Check table names
    assert DBProject.__tablename__ == "projects", "DBProject table name"
    assert DBDrugParameter.__tablename__ == "drug_parameters", "DBDrugParameter table name"
    
    print("✓ Database models OK")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("MedDesign MVP - Integration Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import test FAILED")
        all_passed = False
    else:
        print("\n✓ All imports successful")
    
    # Test 2: Calculator
    try:
        if not test_calculator():
            all_passed = False
    except Exception as e:
        print(f"❌ Calculator test FAILED: {e}")
        all_passed = False
    
    # Test 3: Database models
    try:
        if not test_database_models():
            all_passed = False
    except Exception as e:
        print(f"❌ Database models test FAILED: {e}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("\nNext steps:")
        print("1. Set up PostgreSQL database")
        print("2. Configure .env with YandexGPT API keys")
        print("3. Run: python main.py")
        print("4. Visit: http://localhost:8000/docs")
    else:
        print("❌ SOME TESTS FAILED - check output above")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
