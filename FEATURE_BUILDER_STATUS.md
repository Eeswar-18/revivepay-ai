Feature builder implementation started in backend/app/core/features.py.
The file contains the build_features function that constructs a feature vector from a Case, Customer, and Merchant.
It includes:
- Case-based features: amount, amount band, case type, etc.
- Merchant-based features: MDR bps, autonomous ceiling, risk appetite (one-hot)
- Customer-based features: lifetime txn count, lifetime success rate, prior recovery success rate, do not contact, mandate active, preferred method (one-hot), segment (one-hot)
- Time-based features: hour of day (sin/cos), day of week (sin/cos), weekend flag
The function uses the virtual clock? Actually, we used the case's occurred_at or detected_at for time features, not the virtual clock. That's correct because features should be based on the event time, not current simulation time.
We still need to write the test file and then run verification.
Next steps:
1. Write backend/tests/test_features.py with comprehensive unit tests.
2. Run the test for features.
3. Run full test suite.
4. Run ruff and mypy.
5. If all passes, update STATUS.md and commit.