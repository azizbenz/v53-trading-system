# VPS Capital Profile Enforcement Spec

Purpose:
- define how the VPS uses governed capital-profile artifacts
- prevent free-form pair selection from a static global config list

## Enforcement flow

1. VPS reads current usable capital.
2. VPS maps usable capital to the lower proven bucket.
3. VPS loads `capital_profiles/{bucket}.json`.
4. VPS validates freshness and hash state.
5. VPS enforces `allowed_pairs`, `max_active_pairs`, and bucket eligibility.

## Bucket mapping rule

- use the lower proven bucket, never a higher bucket
- if current usable capital falls below the current bucket, downgrade bucket or block
- if current usable capital exceeds the highest proven bucket, keep using the highest lower proven bucket until a higher artifact exists

Examples:
- `470 USDT` -> use bucket `400`
- `1480 USDT` -> use bucket `500` or `1000` if defined and proven, never `1500`

## Missing / stale / invalid artifact behavior

If capital profile artifact is missing, stale, or hash-invalid:

- shadow: no green readiness
- micro-live: no submit
- live: no submit

Reason codes:

- `CAPITAL_PROFILE_MISSING`
- `CAPITAL_PROFILE_STALE`
- `CAPITAL_PROFILE_HASH_INVALID`

## Pair eligibility rule

If pair not in `allowed_pairs`:

- do not trade
- emit `no_trade_reason = PAIR_NOT_ALLOWED_FOR_CAPITAL_BUCKET`

## Max active pairs rule

If active positions already meet or exceed `max_active_pairs`:

- block lower-ranked candidates
- emit `no_trade_reason = MAX_ACTIVE_PAIRS_EXCEEDED_FOR_CAPITAL_BUCKET`

## Safety rules

- config capital is not sufficient for live/shadow promotion
- missing balance cannot select a higher bucket
- missing capital profile cannot green micro-live/live readiness
- pair presence in config is not proof of bucket eligibility
