# Build-1 to Build-5 External Audit Questions

Date: `2026-05-01`

1. Should `cockpit` be part of the canonical staged build order, or should it be excluded consistently from both inventory and Build-1 smoke governance?
2. Is direct `cockpit -> data_backbone` dependency doctrinally acceptable, or must cockpit consume only a narrower projection/adapter layer?
3. Should `run_build9_core_smoke.py` continue to fail Build-1 on repo-wide engineering guardrails, or should the smoke gate be narrowed to a smaller governed subset?
4. Is Build-3 allowed to remain `PARTIAL` while safety behavior is strong but measured fill/cost realism is still incomplete?
5. Is Build-4 allowed to remain `PARTIAL` while baseline caps and explicit non-green statuses exist but true drawdown and capital-readiness rails remain open?
6. Is Build-5 allowed to remain `PARTIAL` while expected CE stays expected-only and cost completeness is carried but not universally complete?
7. Does the cockpit need explicit Build-1 build-health visibility before Shadow, or is repo-level smoke/test evidence sufficient for the current operator doctrine?
