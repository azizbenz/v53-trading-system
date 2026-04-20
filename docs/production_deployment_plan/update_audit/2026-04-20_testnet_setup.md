# Binance Spot Testnet Setup

## Objective

Document the bounded operator setup required to run the governed Binance Spot testnet integration checks without leaking credentials into the repository.

## Steps

1. Generate Binance Spot testnet API credentials manually at [testnet.binance.vision](https://testnet.binance.vision/).
2. Export the dedicated environment variables before running the test:

```powershell
$env:BINANCE_TESTNET_API_KEY="..."
$env:BINANCE_TESTNET_SECRET="..."
$env:BINANCE_TESTNET_LABEL="testnet"
```

Or on POSIX shells:

```bash
export BINANCE_TESTNET_API_KEY="..."
export BINANCE_TESTNET_SECRET="..."
export BINANCE_TESTNET_LABEL="testnet"
```

3. Collect the governed integration surface:

```bash
python -m pytest tests/test_venue_adapters/test_integration_testnet.py -v --collect-only
```

4. Execute the live testnet checks only when the credentials are present:

```bash
python -m pytest tests/test_venue_adapters/test_integration_testnet.py -v
```

## Notes

- The test file skips entirely when `BINANCE_TESTNET_API_KEY` or `BINANCE_TESTNET_SECRET` is absent.
- Do not commit `.env`, `.env.testnet`, or any plaintext credential artifact.
- The test uses `https://testnet.binance.vision` only. There is no fallback to mainnet.
