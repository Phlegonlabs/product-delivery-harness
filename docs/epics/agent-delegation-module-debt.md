# Agent Delegation Module Debt

Status: complete

Superseded scope: the owner clarified on 2026-09-29 that the 500-line hard cap belongs only in the consumer AGENTS template. This source-repository inventory is retained as historical evidence, not an active migration backlog or test exemption list. No Harness module split is required by this task.

Baseline: `b591a618ba8454da8b9ec22b6ea633def2203c24`. Measured physical lines in tracked source and test modules. Excluded documentation, README files, lockfiles, binary assets, data fixtures, and generated, vendor, dependency, build, or minified paths.

Baseline count over 500 lines: 76. The working-tree scan when this debt record was added found the same 76 paths. These entries are migration debt only; they do not exempt a new module from the 500-line limit.

| Baseline lines | Path |
| ---: | --- |
| 581 | install.ps1 |
| 510 | install.sh |
| 2510 | skills/delivery-harness/scripts/archive_run.py |
| 570 | skills/delivery-harness/scripts/check_delivery_acceptance.py |
| 911 | skills/delivery-harness/scripts/check_deployment.py |
| 542 | skills/delivery-harness/scripts/check_ui_contract.py |
| 547 | skills/delivery-harness/scripts/harness_authorization.py |
| 2493 | skills/delivery-harness/scripts/harness_contract_join.py |
| 859 | skills/delivery-harness/scripts/harness_core.py |
| 820 | skills/delivery-harness/scripts/harness_git.py |
| 1016 | skills/delivery-harness/scripts/harness_graph.py |
| 8106 | skills/delivery-harness/scripts/harness_manifest.py |
| 5268 | skills/delivery-harness/scripts/harness_transition.py |
| 1266 | skills/delivery-harness/scripts/harness_ui_evidence.py |
| 983 | skills/delivery-harness/scripts/harness_worker_result_transition.py |
| 803 | skills/delivery-harness/scripts/inspect_harness_run.py |
| 503 | skills/delivery-harness/scripts/new_run.py |
| 839 | skills/delivery-harness/scripts/parity_capture.py |
| 2056 | skills/delivery-harness/scripts/push_archived_candidate.py |
| 682 | skills/delivery-harness/scripts/push_integration_branch.py |
| 1613 | skills/delivery-harness/scripts/select_ready_nodes.py |
| 1624 | skills/delivery-harness/scripts/tests/manifest_fixtures.py |
| 1221 | skills/delivery-harness/scripts/tests/test_archive_run.py |
| 623 | skills/delivery-harness/scripts/tests/test_candidate_resume.py |
| 1347 | skills/delivery-harness/scripts/tests/test_close_wave.py |
| 793 | skills/delivery-harness/scripts/tests/test_delivery_acceptance.py |
| 856 | skills/delivery-harness/scripts/tests/test_deployment_record.py |
| 2396 | skills/delivery-harness/scripts/tests/test_graph_orchestration.py |
| 976 | skills/delivery-harness/scripts/tests/test_harness_e2e.py |
| 572 | skills/delivery-harness/scripts/tests/test_harness_git.py |
| 3184 | skills/delivery-harness/scripts/tests/test_harness_manifest.py |
| 779 | skills/delivery-harness/scripts/tests/test_harness_strict_authority.py |
| 504 | skills/delivery-harness/scripts/tests/test_harness_transition.py |
| 1164 | skills/delivery-harness/scripts/tests/test_harness_ui_evidence.py |
| 1756 | skills/delivery-harness/scripts/tests/test_harness_v11.py |
| 514 | skills/delivery-harness/scripts/tests/test_hybrid_cross_skill_publication.py |
| 559 | skills/delivery-harness/scripts/tests/test_inspect_parent_drift.py |
| 944 | skills/delivery-harness/scripts/tests/test_install_script.py |
| 537 | skills/delivery-harness/scripts/tests/test_lifecycle_golden_path.py |
| 1542 | skills/delivery-harness/scripts/tests/test_node_transitions.py |
| 569 | skills/delivery-harness/scripts/tests/test_parity_capture.py |
| 1103 | skills/delivery-harness/scripts/tests/test_push_archived_candidate.py |
| 615 | skills/delivery-harness/scripts/tests/test_push_path.py |
| 509 | skills/delivery-harness/scripts/tests/test_security_requirements_join.py |
| 519 | skills/delivery-harness/scripts/tests/test_security_review_result.py |
| 3179 | skills/delivery-harness/scripts/tests/test_select_ready_nodes.py |
| 1575 | skills/delivery-harness/scripts/tests/test_skill_contract.py |
| 1754 | skills/delivery-harness/scripts/tests/test_validate_harness_plan.py |
| 1530 | skills/delivery-harness/scripts/tests/test_validate_worker_result.py |
| 1983 | skills/delivery-harness/scripts/tests/test_verifier_runtime.py |
| 1827 | skills/delivery-harness/scripts/tests/test_write_path_transitions.py |
| 537 | skills/delivery-harness/scripts/trusted_host_publication.py |
| 1971 | skills/delivery-harness/scripts/validate_worker_result.py |
| 2640 | skills/delivery-harness/scripts/verifier_runtime.py |
| 1653 | skills/design-system-compiler/scripts/check_design_system_pair.py |
| 1655 | skills/design-system-compiler/scripts/tests/test_check_design_system_pair.py |
| 2259 | skills/product-activation/scripts/check_activation.py |
| 1055 | skills/product-activation/scripts/tests/test_check_activation.py |
| 1537 | skills/product-definition-builder/scripts/check_outcome_review.py |
| 3406 | skills/product-definition-builder/scripts/check_product_package.py |
| 548 | skills/product-definition-builder/scripts/prd_ui_contract.py |
| 521 | skills/product-definition-builder/scripts/product_agent_graph.cjs |
| 519 | skills/product-definition-builder/scripts/tests/test_outcome_review.py |
| 2794 | skills/product-definition-builder/scripts/tests/test_product_package_checker.py |
| 2935 | skills/product-definition-builder/scripts/tests/test_skill_contract.py |
| 719 | skills/seo-growth-review/scripts/check_seo_review.py |
| 514 | skills/seo-growth-review/scripts/tests/test_check_seo_review.py |
| 522 | skills/ui-design-builder/assets/templates/HIFI_REVIEWER.template.html |
| 2746 | skills/ui-design-builder/assets/templates/WIREFRAMES.template.html |
| 2633 | skills/ui-design-builder/assets/templates/WIREFRAMES_V4.template.html |
| 3566 | skills/ui-design-builder/scripts/check_ui_design_contract.py |
| 2663 | skills/ui-design-builder/scripts/check_wireframe_html.py |
| 755 | skills/ui-design-builder/scripts/hifi_reviewer.py |
| 645 | skills/ui-design-builder/scripts/tests/test_reviewer_browser.py |
| 1731 | skills/ui-design-builder/scripts/tests/test_ui_design_contract.py |
| 1573 | skills/ui-design-builder/scripts/tests/test_wireframe_contract.py |
