"""
V5.3 — Data Backbone: reliable, observable data ingestion pipeline.

Sub-modules (in build order):
1. websocket_gateway — connection, subscription, heartbeat, reconnect, raw messages
2. rest_bootstrap — snapshots, rate limiting, gap fill, reporting
3. event_normalizer — schema mapping, timestamps, classification, validation
4. internal_router — consumer registry, priority dispatch, queues, backpressure
5. freshness_checker — age tracking, stale penalties, hard blocks
6. consistency_checker — sequences, gaps, duplicates, contradictions
7. pair_health_scorer — quality aggregation, suspension, recovery, health state
"""
