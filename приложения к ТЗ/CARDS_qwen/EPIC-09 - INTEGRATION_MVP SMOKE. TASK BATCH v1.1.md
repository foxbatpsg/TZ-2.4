# EPIC-09 — INTEGRATION & RESILIENCE. TASK BATCH v1.1

Status: Ready for CODE-agent handoff.
Dependencies: formally per Dependency Matrix — EPIC-01, EPIC-02, EPIC-03, EPIC-04, EPIC-05, EPIC-06, EPIC-07, EPIC-08. Transitively — all previous.
EPIC Goal: Assemble the full route `GUI → Application/Core → Research Engine → MCP/LLM → Search Core → Data Layer` and verify all resilience scenarios. The integration layer is thin glue between existing components, not a parallel architecture.
Gate G-09: Recovery does not lose valid saved data and does not violate FSM. All cross-scenarios from TZ Section 1, Section 2.3 pass.

## Common invariants and prohibitions for all EPIC-09 tasks

ALLOWED_FILES (global for EPIC):

- `src/integration/` (root directory of integration layer)
- `src/integration/__init__.py`
- `src/integration/service_registry.py`
- `src/integration/workspace.py`
- `src/integration/config_loader.py`
- `src/integration/storage_adapter.py`
- `src/integration/fsm_adapter.py`
- `src/integration/mcp_adapter.py`
- `src/integration/llm_adapter.py`
- `src/integration/orchestrator.py`
- `src/integration/step_executor.py`
- `src/integration/artifact_collector.py`
- `src/integration/progress_aggregator.py`
- `src/integration/log_bridge.py`
- `src/integration/gui_intent_bridge.py`
- `src/integration/gui_state_bridge.py`
- `src/integration/gui_settings_bridge.py`
- `src/integration/gui_observability_bridge.py`
- `src/integration/mcp_watchdog.py`
- `src/integration/resilience_scenarios.py`
- `src/integration/smoke.py`
- `src/integration/acceptance.py`
- `tests/integration/`
- `tests/fixtures/` (fake adapters, stubs)

FORBIDDEN (global for EPIC):

- Creating parallel architecture with own ports that do not correspond to real interfaces from EPIC-02…08.
- Direct modification of `status` on `Study`, `ResearchSession`, `SearchTask` bypassing FSM.
- Direct write to SQLite bypassing DB-write layer.
- Using real network in tests.
- Using real LLM in tests.
- Modifying contracts from previous EPICs.
- Creating own DB tables that are not part of the domain schema from TZ Section 3.

Global integration rule:
The integration layer of EPIC-09 is thin glue between existing components:

- `ResearchEngine` (EPIC-05) — research cycle orchestrator
- `SearchCore` (EPIC-04) — search core
- `LLMBackend` (EPIC-06) — LLM backend interface
- `MCPTransport` (EPIC-07) — transport layer
- `DB-write layer` (EPIC-02) — unified write layer
- `FSM` (EPIC-03) — formal state machines
- `GUI` (EPIC-08) — user interface

The integration layer does not create its own ports duplicating these interfaces. It registers real components in `ServiceRegistry` and ensures their interaction.

---

## G1 — Integration contracts and working environment

### TASK-09-01: Service registry and registration of real components

GOAL: Create a service registry that registers real components from EPIC-02…08.

CONTEXT: The integration layer does not create its own ports. It registers real interfaces: `ResearchEngine`, `SearchCore`, `LLMBackend`, `MCPTransport`, `DB-write layer`, `FSM`, `GUI`.

ALLOWED_FILES: `src/integration/__init__.py`, `src/integration/service_registry.py`, `tests/integration/test_service_registry.py`.

FORBIDDEN: Creating own ports duplicating real interfaces. Implementing business logic. Network calls.

IMPLEMENTATION DETAILS:

- `ServiceRegistry` provides registration and retrieval of services by name.
- Registered services (real interfaces from previous EPICs):
    - `research_engine` → `ResearchEngine` (EPIC-05)
    - `search_core` → `SearchCore` (EPIC-04)
    - `llm_backend` → `LLMBackend` (EPIC-06)
    - `mcp_transport` → `MCPTransport` (EPIC-07)
    - `db_writer` → `DBWriteLayer` (EPIC-02)
    - `study_fsm` → `StudyFSM` (EPIC-03)
    - `session_fsm` → `ResearchSessionFSM` (EPIC-03)
    - `task_fsm` → `SearchTaskFSM` (EPIC-03)
    - `mcp_operation_fsm` → `MCPOperationFSM` (EPIC-03)
    - `llm_backend_fsm` → `LLMBackendFSM` (EPIC-03)
    - `job_fsm` → `JobFSM` (EPIC-03)
    - `gui_coordinator` → `ThreadCoordinator` (EPIC-08)
- Registry is immutable after `freeze()` phase.
- Tests use fake implementations of interfaces.

TESTS:

- `test_registry_registers_real_interfaces`
- `test_registry_freeze_prevents_new_services`
- `test_unknown_service_raises_error`
- `test_all_required_services_registered`
- `test_all_six_state_machines_registered`

ACCEPTANCE: Registry contains all real components including all six FSMs from State Machine Spec v1.1. No own ports duplicating interfaces.

STOP_CONDITIONS: If any interface from previous EPICs is not defined — stop the task.

---

### TASK-09-02: Bootstrap of working directory and project structure

GOAL: Implement idempotent creation of working directory with project structure from TZ Section 3, Section 25.

CONTEXT: TZ Section 3, Section 25 defines: `data/projects/{project_id}.db` — project DB, `registry.db` — global registry.

ALLOWED_FILES: `src/integration/workspace.py`, `tests/integration/test_workspace_bootstrap.py`.

FORBIDDEN: Writing outside the provided `workspace`. Accessing network. Starting LLM or MCP.

IMPLEMENTATION DETAILS:

- `bootstrap_workspace(workspace_path)` creates structure:
    - `data/` — root data directory
    - `data/projects/` — project DB directory
    - `data/registry.db` — global registry
    - `logs/` — logs directory
    - `settings/` — settings directory
- Creates `environment_manifest.json` with `schema_version`, `created_at`, `mode=local_cpu_only`.
- Repeated call does not duplicate files or break existing data.
- Creates `ProjectRegistry` in `registry.db` (tables `ProjectRegistry`, `GlobalDocumentIndex`, `GlobalSourceIndex` from TZ Section 3, Section 25).

TESTS:

- `test_workspace_directories_created`
- `test_registry_db_created_with_tables`
- `test_manifest_written_once`
- `test_bootstrap_is_idempotent`
- `test_manifest_contains_local_mode`

ACCEPTANCE: Working directory is ready. Structure matches TZ Section 3, Section 25.

STOP_CONDITIONS: If structure from TZ has changed — stop the task.

---

### TASK-09-03: Integration config loader

GOAL: Implement loading and validation of configuration compatible with `ResearchConfig` from TZ Section 2, Section 8.

CONTEXT: TZ Section 2, Section 8 defines `ResearchConfig` with sections: `search`, `retrieval`, `ranking`, `deduplication`, `sufficiency`, `budget`, `llm`, `mcp`, `sources`, `chunking`, `reporting`, `storage`.

ALLOWED_FILES: `src/integration/config_loader.py`, `tests/integration/test_integration_config.py`.

FORBIDDEN: Reading files outside `tmp_path` in tests. Making network requests. Changing research state.

IMPLEMENTATION DETAILS:

- `IntegrationConfigLoader` loads and validates configuration.
- Configuration is compatible with `ResearchConfig` from TZ Section 2, Section 8.
- Includes fields for integration:
    - `workspace_path`, `db_path`, `registry_path`
    - `log_level`, `smoke_mode`
    - `llm` (compatible with `ResearchConfig.llm` from EPIC-06)
    - `budget` (compatible with `ResearchConfig.budget`)
- Corrupted JSON returns defaults and a list of warnings.
- Path validation is performed without creating extra files.

TESTS:

- `test_defaults_are_applied`
- `test_valid_config_loaded`
- `test_corrupt_json_returns_defaults`
- `test_config_compatible_with_research_config`
- `test_llm_section_includes_context_budget_fields`

ACCEPTANCE: Configuration is compatible with `ResearchConfig`. Errors do not cause crash.

STOP_CONDITIONS: If `ResearchConfig` structure has changed — stop the task.

---

## G2 — Storage, FSM, MCP and LLM adapters

### TASK-09-04: Integration with SQLite domain schema

GOAL: Provide integration access to domain schema from TZ Section 3 through existing `DB-write layer`.

CONTEXT: The integration layer does not create its own tables. It uses existing tables from the domain schema: `Study`, `ResearchSession`, `SearchTask`, `LogRecord`, `Job`, `Evidence`, `Claim`, etc.

ALLOWED_FILES: `src/integration/storage_adapter.py`, `tests/integration/test_storage_adapter.py`.

FORBIDDEN: Creating own tables that are not part of the domain schema. Direct write bypassing `DB-write layer`. Modifying schema from EPIC-02.

IMPLEMENTATION DETAILS:

- `StorageAdapter` provides read/write access to domain tables through `DB-write layer` from EPIC-02.
- Methods:
    - `get_study(study_id)` — read `Study`
    - `get_session(session_id)` — read `ResearchSession`
    - `get_log_records(study_id, limit)` — read `LogRecord`
    - `get_job(job_id)` — read `Job`
    - `get_evidence_count(study_id)` — count `Evidence`
    - `get_claim_count(study_id)` — count `Claim`
- All writes go through `DB-write layer`.
- Check `journal_mode=WAL` and `PRAGMA foreign_keys=ON` through connection factory from EPIC-02.

TESTS:

- `test_wal_mode_enabled`
- `test_foreign_keys_enabled`
- `test_read_study_through_adapter`
- `test_write_only_through_db_write_layer`
- `test_no_custom_tables_created`

ACCEPTANCE: Data access through existing domain schema. No own tables.

STOP_CONDITIONS: If `DB-write layer` from EPIC-02 is not available — stop the task.

---

### TASK-09-05: FSM adapter with real triggers

GOAL: Implement an adapter that translates integration commands to real FSM triggers from State Machine Spec v1.1.

CONTEXT: State Machine Spec v1.1 defines real triggers for `Study`: `START_PLANNING`, `PLAN_APPROVED`, `CANCEL_PLANNING`, `START_RESEARCH`, `PAUSE`, `RESUME`, `SOFT_STOP`, `HARD_STOP`, `BUDGET_ZERO`, `BUDGET_FREEZE`, `BUDGET_EXTENDED`, `FINALIZE_PARTIAL`, `STOP_SUFFICIENT`, `STOP_NO_INFORMATION_GAIN`, `STOP_NO_AVAILABLE_SOURCES`, `REPORT_VALID`, `FINALIZATION_ERROR`, `CRITICAL_ERROR`, `ARCHIVE`.

ALLOWED_FILES: `src/integration/fsm_adapter.py`, `tests/integration/test_fsm_adapter.py`.

FORBIDDEN: Using invented commands (`START`, `STOP`, `RETRY`, `RESET`, `FINISH_SMOKE`). Direct modification of `.status`. Mixing commands and states.

IMPLEMENTATION DETAILS:

- `FsmAdapter` implements a bridge between integration commands and real triggers.
- Mapping of commands to real triggers:

        Integration command → Real trigger:
        START_PLANNING → START_PLANNING
        PLAN_APPROVED → PLAN_APPROVED
        CANCEL_PLANNING → CANCEL_PLANNING
        START_RESEARCH → START_RESEARCH
        PAUSE → PAUSE
        RESUME → RESUME
        SOFT_STOP → SOFT_STOP
        HARD_STOP → HARD_STOP
        BUDGET_ZERO → BUDGET_ZERO
        BUDGET_FREEZE → BUDGET_FREEZE
        BUDGET_EXTENDED → BUDGET_EXTENDED
        FINALIZE_PARTIAL → FINALIZE_PARTIAL
        STOP_SUFFICIENT → STOP_SUFFICIENT
        STOP_NO_INFORMATION_GAIN → STOP_NO_INFORMATION_GAIN
        STOP_NO_AVAILABLE_SOURCES → STOP_NO_AVAILABLE_SOURCES
        REPORT_VALID → REPORT_VALID
        FINALIZATION_ERROR → FINALIZATION_ERROR
        CRITICAL_ERROR → CRITICAL_ERROR
        ARCHIVE → ARCHIVE

- `snapshot()` returns a read-only projection with `state`, `progress`, `error_code`.
- Tests must use real `StudyFSM` from EPIC-03, not a fake.

TESTS:

- `test_start_planning_command_maps_correctly`
- `test_plan_approved_command_maps_correctly`
- `test_cancel_planning_command_maps_correctly`
- `test_start_research_command_maps_correctly`
- `test_soft_stop_command_maps_to_soft_stop`
- `test_hard_stop_command_maps_to_hard_stop`
- `test_budget_zero_command_maps_to_budget_zero`
- `test_stop_sufficient_command_maps_correctly`
- `test_stop_no_information_gain_command_maps_correctly`
- `test_stop_no_available_sources_command_maps_correctly`
- `test_critical_error_command_maps_correctly`
- `test_finalization_error_command_maps_correctly`
- `test_unknown_command_rejected`
- `test_snapshot_is_read_only`
- `test_all_study_triggers_are_mapped`

ACCEPTANCE: All commands map to real triggers from State Machine Spec v1.1. No invented commands. All 19 Study triggers are mapped.

STOP_CONDITIONS: If triggers from State Machine Spec v1.1 have changed — stop the task.

---

### TASK-09-06: MCP adapter with `MCPTransport` integration and `stdout` protection

GOAL: Implement MCP client adapter integrated with real `MCPTransport` from EPIC-07 and checking `stdout` protection.

CONTEXT: EPIC-07 implements `MCPTransport` with `stdout` protection. Integration adapter must use real transport and check that `stdout` contains only JSON-RPC.

ALLOWED_FILES: `src/integration/mcp_adapter.py`, `tests/integration/test_mcp_adapter.py`.

FORBIDDEN: Starting real MCP server in tests. Real LLM. Bypassing `stdout` protection.

IMPLEMENTATION DETAILS:

- `McpAdapter` accepts `MCPTransport` from EPIC-07.
- Method `invoke_tool(name, payload)` calls real transport.
- For tests provide `FakeMCPTransport` with deterministic responses.
- `stdout` protection check: all responses must be valid JSON-RPC.
- Timeouts and errors are translated to `McpToolError`.
- Support for mandatory fields from `MCP TOOL CONTRACTS v1.1`.

TESTS:

- `test_invoke_tool_returns_payload`
- `test_timeout_maps_to_error`
- `test_unknown_tool_rejected`
- `test_stdout_contains_only_json_rpc`
- `test_fake_transport_is_deterministic`

ACCEPTANCE: Adapter is integrated with real `MCPTransport`. `stdout` protection is checked.

STOP_CONDITIONS: If `MCPTransport` from EPIC-07 is not available — stop the task.

---

### TASK-09-07: LLM stub implementing `LLMBackend` from EPIC-06

GOAL: Implement deterministic LLM stub implementing `LLMBackend` interface from EPIC-06, with `TokenBudgetManager` integration.

CONTEXT: EPIC-06 defines `LLMBackend` interface with methods `generate()`, `health_check()`, `get_context_info()`. Also EPIC-06 defines `TokenBudgetManager` for context budget management.

ALLOWED_FILES: `src/integration/llm_adapter.py`, `tests/integration/test_llm_adapter.py`.

FORBIDDEN: Loading models. Network access. GPU usage. Real generation.

IMPLEMENTATION DETAILS:

- `LocalStubLLM` implements `LLMBackend` interface from EPIC-06.
- Methods:
    - `generate(prompt, max_tokens, temperature, response_format)` — deterministic response from request hash.
    - `health_check()` — returns `HealthStatus` (HEALTHY, DEGRADED, UNREACHABLE).
    - `get_context_info()` — returns `ContextInfo(backend_reported_context=4096)`.
- Support for modes `ok`, `slow`, `fail` via stub config.
- Integration with `TokenBudgetManager` from EPIC-06: check `evidence_budget` before generation.
- Accounting of `cpu_budget` and `max_tokens` as metadata.

TESTS:

- `test_stub_response_is_deterministic`
- `test_fail_mode_raises_executor_error`
- `test_health_check_returns_valid_status`
- `test_get_context_info_returns_context_info`
- `test_token_budget_manager_integration`
- `test_no_network_is_used`

ACCEPTANCE: Stub implements real `LLMBackend` interface. `TokenBudgetManager` integration works.

STOP_CONDITIONS: If `LLMBackend` interface from EPIC-06 has changed — stop the task.

---

## G3 — Research loop and observability

### TASK-09-08: Start orchestrator via `ResearchEngine`

GOAL: Implement research start orchestrator using real `ResearchEngine` from EPIC-05.

CONTEXT: EPIC-05 implements `ResearchEngine` — research cycle orchestrator. Integration layer calls `ResearchEngine.start()`, does not implement its own logic.

ALLOWED_FILES: `src/integration/orchestrator.py`, `tests/integration/test_orchestrator_start.py`.

FORBIDDEN: Duplicating `ResearchEngine` business logic. Direct modification of statuses. Network calls.

IMPLEMENTATION DETAILS:

- `ResearchOrchestrator.start()` calls `ResearchEngine.start()` from EPIC-05.
- Configuration and form validation before start.
- Sending `START_RESEARCH` command through `FsmAdapter` (TASK-09-05).
- On validation error returns structured report without starting.
- Check that `Study.status == READY` before start.

TESTS:

- `test_start_calls_research_engine`
- `test_invalid_form_blocks_start`
- `test_start_sends_fsm_command`
- `test_duplicate_start_is_rejected`
- `test_study_must_be_ready_before_start`

ACCEPTANCE: Start goes through real `ResearchEngine`. No business logic duplication.

STOP_CONDITIONS: If `ResearchEngine` from EPIC-05 is not available — stop the task.

---

### TASK-09-09: Step executor with adaptive cycle and `SufficiencyEvaluator`

GOAL: Implement execution of one research step with integration of adaptive cycle and `SufficiencyEvaluator`.

CONTEXT: TZ Section 1, Section 6 defines adaptive search cycle. After each step `SufficiencyEvaluator` makes a decision to continue or stop.

ALLOWED_FILES: `src/integration/step_executor.py`, `tests/integration/test_step_executor.py`.

FORBIDDEN: Executing the entire research cycle. Real LLM. Network calls. Bypassing `SufficiencyEvaluator`.

IMPLEMENTATION DETAILS:

- `StepExecutor.execute()` accepts `step_spec` and returns `step_result`.
- Uses `LocalStubLLM` and `McpAdapter`.
- After each step calls `SufficiencyEvaluator` from EPIC-05.
- Checks decision: `CONTINUE`, `STOP_SUFFICIENT`, `STOP_BUDGET`, `STOP_NO_INFORMATION_GAIN`, `STOP_NO_AVAILABLE_SOURCES`.
- Results contain `status`, `outputs`, `errors`, `duration_ms`, `sufficiency_decision`.
- Tool and LLM errors are classified separately.

TESTS:

- `test_successful_step_returns_outputs`
- `test_sufficiency_evaluator_called_after_step`
- `test_continue_decision_allows_next_step`
- `test_stop_decision_blocks_next_step`
- `test_llm_failure_is_captured`
- `test_mcp_failure_is_captured`

ACCEPTANCE: Step is integrated into adaptive cycle. `SufficiencyEvaluator` is called after each step.

STOP_CONDITIONS: If `SufficiencyEvaluator` from EPIC-05 is not available — stop the task.

---

### TASK-09-10: Artifact collector with `Evidence` and `Claim` integration

GOAL: Implement saving of step results with integration of domain entities `Evidence` and `Claim`.

CONTEXT: TZ Section 3 defines `Evidence` and `Claim` as domain entities. Artifacts must be linked to them.

ALLOWED_FILES: `src/integration/artifact_collector.py`, `tests/integration/test_artifact_collector.py`.

FORBIDDEN: Uploading artifacts to network. Modifying original results. Writing bypassing `DB-write layer`.

IMPLEMENTATION DETAILS:

- `ArtifactCollector.save()` writes file and record through `DB-write layer`.
- Supports types `text`, `json`, `report`.
- For `Evidence` and `Claim`: link to domain entities via `evidence_id` / `claim_id`.
- File names are sanitized.
- Repeated write with same `artifact_id` is idempotent.

TESTS:

- `test_text_artifact_saved`
- `test_json_artifact_roundtrip`
- `test_evidence_artifact_linked_to_domain_entity`
- `test_claim_artifact_linked_to_domain_entity`
- `test_duplicate_artifact_id_is_idempotent`

ACCEPTANCE: Artifacts are linked to domain entities. Write through `DB-write layer`.

STOP_CONDITIONS: If `DB-write layer` is not available — stop the task.

---

### TASK-09-11: Progress aggregator with `ResearchSession.iteration` integration

GOAL: Implement aggregation of step events into progress with integration of `ResearchSession.iteration`.

CONTEXT: TZ Section 3, Section 18 defines `ResearchSession.iteration` — current cycle iteration. Progress must be linked to iterations.

ALLOWED_FILES: `src/integration/progress_aggregator.py`, `tests/integration/test_progress_aggregator.py`.

FORBIDDEN: Direct modification of statuses. Real timers in tests. Network requests.

IMPLEMENTATION DETAILS:

- `ProgressAggregator` accepts events `step_started`, `step_finished`, `step_failed`.
- Computes `percent`, `stage`, `last_error`, `current_iteration`.
- `current_iteration` is synchronized with `ResearchSession.iteration` through `DB-write layer`.
- Supports deterministic stage order.
- Progress is clamped to range 0–100.

TESTS:

- `test_percent_updates_on_finished_steps`
- `test_current_iteration_synced_with_session`
- `test_failed_step_sets_last_error`
- `test_out_of_order_events_are_safe`
- `test_progress_is_clamped`

ACCEPTANCE: Progress is synchronized with `ResearchSession.iteration`. Events do not mutate statuses.

STOP_CONDITIONS: If `ResearchSession` is not available — stop the task.

---

### TASK-09-12: Core events bridge to log stream via `LogRecord`

GOAL: Implement transmission of orchestrator, LLM stub and MCP events to log stream via `LogRecord` from EPIC-02.

CONTEXT: TZ Section 3 defines `LogRecord` as domain entity. Logs must be written through `DB-write layer`.

ALLOWED_FILES: `src/integration/log_bridge.py`, `tests/integration/test_log_bridge.py`.

FORBIDDEN: Writing secrets. Network calls. Direct write bypassing `DB-write layer`.

IMPLEMENTATION DETAILS:

- `LogBridge` writes events through `DB-write layer` to `LogRecord` table.
- Levels `DEBUG`, `INFO`, `WARN`, `ERROR`.
- Events contain `entity_type`, `entity_id`, `from_state`, `to_state`, `trigger`, `component`, `timestamp` (7 fields from TZ).
- Support ring buffer for test checks.
- For X-Ray Activity Stream: event types from TZ Section 6, Section 5 (`SEARCH`, `RANKING`, `FETCH`, `PARSING`, `CHUNKING`, `EVIDENCE_EXTRACTION`, `GAP_DETECTION`, `ERROR`).

TESTS:

- `test_events_are_captured_by_level`
- `test_log_record_has_seven_fields`
- `test_xray_event_types_are_defined`
- `test_buffer_is_bounded`
- `test_no_secrets_in_messages`

ACCEPTANCE: Logs are written through `DB-write layer` to `LogRecord`. All 7 fields are present.

STOP_CONDITIONS: If `LogRecord` from EPIC-02 is not available — stop the task.

---

## G4 — GUI binding with integration core

### TASK-09-13: GUI intent bridge to FSM commands (including `SOFT_STOP`, `HARD_STOP`)

GOAL: Bind GUI intents to integration commands and FSM, including `SOFT_STOP` and `HARD_STOP`.

CONTEXT: EPIC-08 v1.1 defines intents: `START_RESEARCH`, `STOP_RESEARCH`, `SOFT_STOP`, `HARD_STOP`, `RETRY`, `RESET`, `SAVE_SETTINGS`, `EXPORT_ARTIFACTS`.

ALLOWED_FILES: `src/integration/gui_intent_bridge.py`, `tests/integration/test_gui_intent_bridge.py`.

FORBIDDEN: Direct modification of statuses. Executing commands outside intent queue. Network calls.

IMPLEMENTATION DETAILS:

- `GuiIntentBridge` accepts `IntentDispatcher` from EPIC-08 and `FsmAdapter` from TASK-09-05.
- Mapping of intents to real triggers:
    - `START_RESEARCH` → `START_RESEARCH`
    - `STOP_RESEARCH` → `SOFT_STOP`
    - `SOFT_STOP` → `SOFT_STOP`
    - `HARD_STOP` → `HARD_STOP`
    - `RETRY` → `RESUME`
    - `RESET` → `ARCHIVE`
- Non-FSM intents handled separately:
    - `SAVE_SETTINGS` → routed to `GuiSettingsBridge` (TASK-09-15), not to FSM.
    - `EXPORT_ARTIFACTS` → routed to `ArtifactCollector` (TASK-09-10), not to FSM.
- Rejects unknown intents with reason.
- Writes mapping audit log to `tmp_path`.

TESTS:

- `test_start_intent_maps_to_start_research`
- `test_stop_research_intent_maps_to_soft_stop`
- `test_soft_stop_intent_maps_to_soft_stop`
- `test_hard_stop_intent_maps_to_hard_stop`
- `test_retry_intent_maps_to_resume`
- `test_reset_intent_maps_to_archive`
- `test_save_settings_intent_routed_to_settings_bridge`
- `test_export_artifacts_intent_routed_to_artifact_collector`
- `test_unknown_intent_rejected`
- `test_mapping_audit_written_to_tmp_path`

ACCEPTANCE: All intents from EPIC-08 are mapped or routed. `SOFT_STOP` and `HARD_STOP` are handled. Non-FSM intents are properly routed.

STOP_CONDITIONS: If `IntentDispatcher` from EPIC-08 is not available — stop the task.

---

### TASK-09-14: FSM snapshot bridge to GUI via `GuiStateSnapshot`

GOAL: Implement transmission of state snapshots from integration to GUI projection via `GuiStateSnapshot` from EPIC-08.

CONTEXT: EPIC-08 v1.1 defines `GuiStateSnapshot` with fields `state`, `progress`, `error_code`, `can_start`, `can_stop`, `updated_at`.

ALLOWED_FILES: `src/integration/gui_state_bridge.py`, `tests/integration/test_gui_state_bridge.py`.

FORBIDDEN: Changing state. Sending commands. Mixing commands and states. Network requests.

IMPLEMENTATION DETAILS:

- `GuiStateBridge` subscribes to `FsmAdapter.snapshot()`.
- Publishes `GuiStateSnapshot` from EPIC-08 for GUI.
- Publishes only when significant fields change.
- Supports manual `refresh()` for deterministic tests.

TESTS:

- `test_snapshot_pushed_on_state_change`
- `test_no_push_when_unchanged`
- `test_error_code_propagated`
- `test_gui_snapshot_is_read_only`
- `test_snapshot_compatible_with_epic08`

ACCEPTANCE: GUI receives only immutable snapshots. Compatible with `GuiStateSnapshot` from EPIC-08.

STOP_CONDITIONS: If `GuiStateSnapshot` from EPIC-08 has changed — stop the task.

---

### TASK-09-15: GUI settings bridge via `SettingsRepository`

GOAL: Bind GUI settings forms to integration config via `SettingsRepository` from EPIC-08.

CONTEXT: EPIC-08 v1.1 defines `SettingsRepository` with atomic write and schema version.

ALLOWED_FILES: `src/integration/gui_settings_bridge.py`, `tests/integration/test_gui_settings_bridge.py`.

FORBIDDEN: Writing outside `tmp_path`. Applying settings without validation. Starting MCP or LLM.

IMPLEMENTATION DETAILS:

- `GuiSettingsBridge` reads form drafts and calls validation.
- Saves result through `SettingsRepository` from EPIC-08.
- On error returns `FormErrors` without writing.
- Supports atomic write through temporary file.

TESTS:

- `test_valid_settings_saved`
- `test_invalid_settings_not_saved`
- `test_atomic_write_used`
- `test_settings_roundtrip_in_tmp_path`
- `test_compatible_with_settings_repository`

ACCEPTANCE: GUI settings and integration config are synchronized via `SettingsRepository`.

STOP_CONDITIONS: If `SettingsRepository` from EPIC-08 is not available — stop the task.

---

### TASK-09-16: GUI observability bridge via EPIC-08 models

GOAL: Bind log streams, artifacts and progress to GUI presentation models from EPIC-08.

CONTEXT: EPIC-08 v1.1 defines `XRayStreamModel`, `ArtifactTableModel`, `ProgressTimelineModel`.

ALLOWED_FILES: `src/integration/gui_observability_bridge.py`, `tests/integration/test_gui_observability_bridge.py`.

FORBIDDEN: Modifying artifacts. Changing statuses. Network requests.

IMPLEMENTATION DETAILS:

- `GuiObservabilityBridge` provides `log_snapshot()`, `artifact_page()`, `progress_snapshot()`.
- Uses `XRayStreamModel`, `ArtifactTableModel`, `ProgressTimelineModel` from EPIC-08.
- Data is returned in read-only structures.
- Supports artifact pagination.

TESTS:

- `test_log_snapshot_reflects_xray_model`
- `test_artifact_page_is_paginated`
- `test_progress_snapshot_is_read_only`
- `test_bridge_does_not_mutate_state`
- `test_compatible_with_epic08_models`

ACCEPTANCE: GUI receives coherent observability through EPIC-08 models.

STOP_CONDITIONS: If models from EPIC-08 are not available — stop the task.

---

## G5 — E2E smoke and MVP acceptance

### TASK-09-17: Happy-path E2E smoke with full cycle from Gate G-05

GOAL: Execute cross-scenario covering the full cycle `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize` from Gate G-05.

CONTEXT: Gate G-05 requires confirmation of the full cycle. E2E test must cover all stages, not a simplified scenario.

ALLOWED_FILES: `src/integration/smoke.py`, `tests/integration/test_e2e_happy_path.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- `run_happy_smoke()` uses `tmp_path`, fake MCP/LLM and local SQLite.
- Full cycle:
    - `bootstrap` — create working directory
    - `config` — load configuration
    - `intent` — create `ResearchIntent`
    - `plan` — generate `ResearchPlan` via `plan_research`
    - `tasks` — create `SearchTask` via `TaskAcceptor`
    - `retrieval` — execute search via `SearchCore`
    - `evidence` — extract `Evidence`
    - `gap` — identify `ResearchGap`
    - `next task` — create new task based on gap
    - `sufficiency` — evaluate via `SufficiencyEvaluator`
    - `finalize` — finalize and save report
- Verify initial Study transitions: `DRAFT → PLANNING → READY → RUNNING`.
- Final report is written to `smoke_report.json`.
- Check that `SufficiencyEvaluator` returned `STOP_SUFFICIENT`.
- Check that `Study.status` transitioned to `FINALIZING`, then to `COMPLETED`.

TESTS:

- `test_smoke_covers_full_cycle`
- `test_initial_study_transitions_draft_to_running`
- `test_sufficiency_returns_stop_sufficient`
- `test_study_reaches_completed`
- `test_artifacts_are_created`
- `test_progress_reaches_100`
- `test_smoke_report_written_to_tmp_path`
- `test_all_fsm_transitions_logged`

ACCEPTANCE: Full cycle from Gate G-05 is covered. All transitions are logged. Initial Study transitions (DRAFT → PLANNING → READY → RUNNING) are verified.

STOP_CONDITIONS: If any component from EPIC-05 is not available — stop the task.

---

### TASK-09-18: Failure/recovery smoke and acceptance report

GOAL: Verify error and recovery scenarios and form acceptance report with Gate G-09 criteria checks.

CONTEXT: Gate G-09: "Recovery does not lose valid saved data and does not violate FSM".

ALLOWED_FILES: `src/integration/acceptance.py`, `tests/integration/test_e2e_failure_recovery.py`.

FORBIDDEN: Hiding errors. Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- `run_failure_smoke()` simulates LLM failure at a step, then `RETRY` and successful completion.
- Checks that error is visible in snapshot, logs and status center.
- Forms `mvp_acceptance_report.json` with results of checks per Gate G-09 criteria:
    - Recovery does not lose valid saved data
    - FSM is not violated
    - `Evidence` and `Claim` are preserved after failure
    - `ResearchSession` transitions to `SESSION_RESUMING`, then to `ACTIVE`
- All files only in `tmp_path`.

TESTS:

- `test_failure_is_reported`
- `test_retry_recovers_run`
- `test_evidence_preserved_after_failure`
- `test_claims_preserved_after_failure`
- `test_session_resumes_correctly`
- `test_acceptance_report_lists_checks`
- `test_no_direct_state_reset_occurs`

ACCEPTANCE: Error is diagnosed and recovered. Data is not lost. Gate G-09 criteria are checked.

STOP_CONDITIONS: If recovery mechanism is not implemented — stop the task.

---

## G6 — Resilience scenarios from TZ and Roadmap

### TASK-09-19: MCP Watchdog (Loop 2)

GOAL: Implement `MCP Watchdog` — independent software watchdog for tracking critical hang of message exchange process.

CONTEXT: TZ Section 5, Section 17 defines Loop 2 (MCP Watchdog). In EPIC-07 audit it was specified that Loop 2 is implemented in EPIC-09.

ALLOWED_FILES: `src/integration/mcp_watchdog.py`, `tests/integration/test_mcp_watchdog.py`.

FORBIDDEN: Violating relational consistency. Damaging DB files. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- `MCPWatchdog` — independent thread tracking JSON-RPC exchange activity.
- If the exchange process completely stops showing signs of activity within the specified critical interval:
    - Forcefully closes the hung MCP server process (terminate).
    - Performs clean restart of MCP server.
    - Extracts from SQLite the current operational memory snapshot and last session checkpoint.
    - Activates `SESSION_RESUMING` mode via `ResearchSessionFSM` and continues interrupted research.
- Watchdog operates in isolation from DBMS.
- Critical interval is configurable (default 60 seconds).
- All state transitions go through formal FSM, not direct assignment.

TESTS:

- `test_watchdog_detects_silent_process`
- `test_watchdog_terminates_and_restarts`
- `test_watchdog_restores_session_state`
- `test_watchdog_activates_session_resuming_via_fsm`
- `test_watchdog_does_not_corrupt_db`
- `test_watchdog_is_isolated_from_db`
- `test_watchdog_uses_fsm_not_direct_assignment`

ACCEPTANCE: Watchdog correctly handles hang. `SESSION_RESUMING` is activated via FSM. DB is not corrupted.

STOP_CONDITIONS: If process restart mechanism is not available in target environment — stop the task.

---

### TASK-09-20: Network resilience scenarios

GOAL: Verify scenarios `network timeout`, `rate-limit`, `source unavailable`, `parse-error`.

CONTEXT: Roadmap v1.2, Section 12 defines network resilience verification. TZ Section 7, Section 23 defines test scenarios.

ALLOWED_FILES: `tests/integration/test_network_resilience.py`.

FORBIDDEN: Real network calls. Modifying production code.

IMPLEMENTATION DETAILS:

- `test_network_timeout`: `FakeSourceAdapter` returns timeout. Verify that `SearchTask` transitions to `FAILED`, `Study` continues operation.
- `test_rate_limit`: `FakeSourceAdapter` returns `RATE_LIMIT`. Verify that retry is not executed.
- `test_source_unavailable`: `FakeSourceAdapter` returns `SOURCE_UNAVAILABLE`. Verify that alternative candidate is selected.
- `test_parse_error`: `FakeSourceAdapter` returns `PARSE_ERROR`. Verify that document is not saved.
- `test_per_domain_concurrency`: verify that concurrent connection limit per domain is enforced.
- `test_exponential_backoff`: verify that retry attempts use exponential delay.
- `test_no_infinite_retries`: verify that retry attempts are bounded.

TESTS:

- The 7 scenarios listed above.
- Check that `Study` does not stop due to one source error.

ACCEPTANCE: All network scenarios are handled. `Study` continues operation on one source error.

STOP_CONDITIONS: If `FakeSourceAdapter` does not support required modes — stop the task.

---

### TASK-09-21: Pause and resume scenarios

GOAL: Verify `pause` and `resume` scenarios for research.

CONTEXT: State Machine Spec v1.1 defines transitions `RUNNING → PAUSED` (trigger: `PAUSE`) and `PAUSED → RUNNING` (trigger: `RESUME`).

ALLOWED_FILES: `tests/integration/test_pause_resume.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- `test_pause_stops_new_tasks`: after `PAUSE` new tasks are not started.
- `test_pause_allows_current_to_finish`: current operations complete.
- `test_resume_continues_from_checkpoint`: after `RESUME` research continues from checkpoint.
- `test_session_suspended_on_pause`: `ResearchSession` transitions to `SUSPENDED`.
- `test_session_active_on_resume`: `ResearchSession` transitions to `ACTIVE`.
- Cross-scenario check: `RUNNING → PAUSED → RUNNING`.

TESTS:

- The 5 scenarios listed above.
- Check `LogRecord` for each transition.

ACCEPTANCE: Pause and resume work correctly. `ResearchSession` is synchronized.

STOP_CONDITIONS: If `PAUSE`/`RESUME` triggers are not available — stop the task.

---

### TASK-09-22: Budget exhaustion scenarios

GOAL: Verify cross-scenario `budget exhaustion / freeze / extension / partial finalization`.

CONTEXT: TZ Section 1, Section 2.3 defines: `RUNNING → BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED → PARTIAL_REPORT`. State Machine Spec v1.1, Section 7 defines Budget Exhaustion cross-scenario.

ALLOWED_FILES: `tests/integration/test_budget_exhaustion.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- `test_budget_zero_triggers_budget_exhausted`: on zero budget `Study` transitions to `BUDGET_EXHAUSTED`.
- `test_budget_freeze`: `BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED` via `BUDGET_FREEZE`.
- `test_budget_extension`: `FREEZE_BUDGET_EXHAUSTED → RUNNING` via `BUDGET_EXTENDED`.
- `test_partial_finalization`: `FREEZE_BUDGET_EXHAUSTED → FINALIZING` via `FINALIZE_PARTIAL`.
- `test_new_task_rejected_on_zero_budget`: `CREATED → VALIDATING → REJECTED_BUDGET`.
- Check that `PARTIAL_REPORT` is metadata, not a state.
- Check cross-scenario from TZ Section 1, Section 2.3.

TESTS:

- The 5 scenarios listed above.
- Check `LogRecord` for each transition.
- Check that `PARTIAL_REPORT` is not a `Study` state.

ACCEPTANCE: All budget scenarios are handled. Cross-scenario from TZ passes.

STOP_CONDITIONS: If budget triggers are not available — stop the task.

---

### TASK-09-23: Interrupted Job scenarios

GOAL: Verify interrupted Job scenarios: bulk indexing, index rebuild, large import.

CONTEXT: TZ Section 4, Section 28 defines Job mechanism. State Machine Spec v1.1, Section 6 defines Job states: `QUEUED → RUNNING → COMPLETED | FAILED | CANCELLED`.

ALLOWED_FILES: `tests/integration/test_interrupted_job.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- `test_job_interrupted_by_system_crash`: Job is interrupted, transitions to `FAILED`.
- `test_job_cancelled_cooperatively`: Job is cancelled via `cancel_job`, transitions to `CANCELLED`.
- `test_job_partial_results_preserved`: partial results are preserved.
- `test_job_restart_after_failure`: Job can be manually restarted.
- Check cooperative cancellation via `threading.Event`.
- Check that `cancel_job` does not assign `Job.status = CANCELLED` directly.

TESTS:

- The 4 scenarios listed above.
- Check cooperative cancellation.

ACCEPTANCE: Interrupted Jobs are handled correctly. Partial results are preserved.

STOP_CONDITIONS: If Job mechanism is not implemented — stop the task.

---

### TASK-09-24: Cross-scenario — Emergency Recovery (LLM Failure)

GOAL: Verify cross-scenario from TZ Section 1, Section 2.3: `RUNNING → LLM_UNAVAILABLE → SESSION_RESUMING → RUNNING`.

CONTEXT: TZ Section 1, Section 2.3 defines: "Emergency recovery: `RUNNING → LLM_UNAVAILABLE → SESSION_RESUMING → RUNNING`". State Machine Spec v1.1, Section 7 defines LLM Failure / Recovery cross-scenario.

ALLOWED_FILES: `tests/integration/test_cross_scenario_llm_failure.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- Cross-scenario:
    - `Study` in state `RUNNING`.
    - LLM Backend transitions to `UNREACHABLE` (trigger: `HEALTH_FAILED`).
    - `ResearchSession` transitions to `LLM_UNAVAILABLE` (trigger: `LLM_BACKEND_UNAVAILABLE`).
    - LLM Backend recovers (`RESTARTING → HEALTHY`).
    - `ResearchSession` transitions to `SESSION_RESUMING` (trigger: `LLM_BACKEND_RECOVERED`).
    - `ResearchSession` transitions to `ACTIVE` (trigger: `RECOVERY_COMPLETE`).
    - `Study` remains in `RUNNING` (TZ: "Research is not required to stop only due to temporary LLM backend unavailability").
- Check that `Evidence` and `Claim` are not lost.
- Check `LogRecord` for each transition.

TESTS:

- `test_llm_failure_cross_scenario`
- `test_study_remains_running`
- `test_evidence_preserved`
- `test_claims_preserved`
- `test_session_resumes_to_active`
- `test_all_transitions_logged`

ACCEPTANCE: Cross-scenario from TZ passes. Data is not lost.

STOP_CONDITIONS: If `LLMBackend` FSM is not available — stop the task.

---

### TASK-09-25: Cross-scenario — User Stop (Soft/Hard Stop)

GOAL: Verify cross-scenarios from TZ Section 1, Section 2.3: Soft Stop and Hard Stop.

CONTEXT: TZ Section 1, Section 2.3 defines:
"User stop: `RUNNING → SOFT_STOP → FINALIZING → COMPLETED | USER_STOPPED`"
State Machine Spec v1.1, Section 7 defines Soft Stop and Hard Stop cross-scenarios.

ALLOWED_FILES: `tests/integration/test_cross_scenario_user_stop.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- Soft Stop scenario:
    - `Study` in state `RUNNING`.
    - Send `SOFT_STOP`.
    - `Study` transitions to `FINALIZING`.
    - Current operations complete.
    - `Study` transitions to `COMPLETED`.
    - `ResearchSession`: `ACTIVE → CLOSING → CLOSED`.
    - `SearchTask`: `RUNNING → COMPLETED`.
- Hard Stop scenario:
    - `Study` in state `RUNNING`.
    - Send `HARD_STOP`.
    - `Study` transitions to `USER_STOPPED`.
    - `ResearchSession`: `ACTIVE → CLOSING → CLOSED`.
    - `SearchTask`: `RUNNING → CANCELLED`.
    - `MCP Operation`: `EXECUTING → CANCELLED`.
    - `Job`: `RUNNING → CANCELLED`.
- Check cooperative cancellation of CPU tasks.
- Check that SQLite remains consistent.

TESTS:

- `test_soft_stop_cross_scenario`
- `test_hard_stop_cross_scenario`
- `test_soft_stop_allows_current_to_finish`
- `test_hard_stop_cancels_all`
- `test_cooperative_cancellation_works`
- `test_sqlite_consistent_after_hard_stop`
- `test_all_transitions_logged`

ACCEPTANCE: Both scenarios from TZ pass. Cooperative cancellation works.

STOP_CONDITIONS: If `SOFT_STOP`/`HARD_STOP` triggers are not available — stop the task.

---

### TASK-09-26: Cross-scenario — Budget Exhaustion

GOAL: Verify cross-scenario from TZ Section 1, Section 2.3: `RUNNING → BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED → PARTIAL_REPORT`.

CONTEXT: TZ Section 1, Section 2.3 defines: "Budget exhaustion: `RUNNING → BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED → PARTIAL_REPORT`".

ALLOWED_FILES: `tests/integration/test_cross_scenario_budget.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- Cross-scenario:
    - `Study` in state `RUNNING`.
    - Budget is exhausted (e.g., `fetch_budget = 0`).
    - `Study` transitions to `BUDGET_EXHAUSTED` (trigger: `BUDGET_ZERO`).
    - `Study` transitions to `FREEZE_BUDGET_EXHAUSTED` (trigger: `BUDGET_FREEZE`).
    - `Study` transitions to `FINALIZING` (trigger: `FINALIZE_PARTIAL`).
    - `Study` transitions to `COMPLETED` (trigger: `REPORT_VALID`).
- Report is marked as `REPORT_TRUNCATED_PARTIAL` (metadata, not state).
- Check that `PARTIAL_REPORT` is not a `Study` state.
- Check that new `SearchTask` is rejected on zero budget.

TESTS:

- `test_budget_exhaustion_cross_scenario`
- `test_partial_report_is_metadata_not_state`
- `test_new_tasks_rejected_on_zero_budget`
- `test_all_transitions_logged`

ACCEPTANCE: Cross-scenario from TZ passes. `PARTIAL_REPORT` is metadata.

STOP_CONDITIONS: If budget triggers are not available — stop the task.

---

### TASK-09-27: Verification of Evidence and Claims preservation after failures

GOAL: Verify that `Evidence` and `Claim` are not lost in any failure scenarios.

CONTEXT: Gate G-09 requires: "Recovery does not lose valid saved data". TZ Section 2, Section 7: "On sudden crash... the program must perform rescue procedure".

ALLOWED_FILES: `tests/integration/test_data_preservation.py`.

FORBIDDEN: Real LLM. Network requests. Direct modification of statuses.

IMPLEMENTATION DETAILS:

- `test_evidence_preserved_after_llm_failure`: after LLM failure all `Evidence` in DB.
- `test_claims_preserved_after_llm_failure`: after LLM failure all `Claim` in DB.
- `test_evidence_preserved_after_hard_stop`: after Hard Stop all `Evidence` in DB.
- `test_claims_preserved_after_hard_stop`: after Hard Stop all `Claim` in DB.
- `test_evidence_preserved_after_budget_exhaustion`: after budget exhaustion all `Evidence` in DB.
- `test_session_state_preserved_after_crash`: after crash `ResearchState` is restored.
- Verification through `DB-write layer`: all data is written atomically.

TESTS:

- The 6 scenarios listed above.
- Check integrity of relational links (`ClaimEvidence`, `EvidenceContextChunk`).

ACCEPTANCE: All data is preserved in any failure scenario. Relational links are not broken.

STOP_CONDITIONS: If checkpoint mechanism is not implemented — stop the task.

---

## Gate G-09 Acceptance Criteria

- Recovery does not lose data: `Evidence`, `Claim`, `ResearchState` are preserved in all failure scenarios.
- FSM is not violated: all transitions go through real triggers from State Machine Spec v1.1.
- LLM Failure cross-scenario: `RUNNING → LLM_UNAVAILABLE → SESSION_RESUMING → RUNNING` passes.
- User Stop cross-scenario: Soft Stop and Hard Stop pass.
- Budget Exhaustion cross-scenario: `RUNNING → BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED → PARTIAL_REPORT` passes.
- Network resilience: `timeout`, `rate-limit`, `unavailable`, `parse-error` are handled.
- Pause/resume: `PAUSE`/`RESUME` work.
- Interrupted Job: partial results are preserved.
- MCP Watchdog: Loop 2 is implemented, hang is handled.
- Full cycle: `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize` passes.
- Integration with real components: no parallel architecture, all through real interfaces.
- No real network calls: all tests on fake adapters.
- No real LLM: all tests on stubs.
- No direct status modification: all transitions through commands.
- All six FSMs are registered in service registry.
- All GUI intents are mapped or properly routed.
- Initial Study transitions (DRAFT → PLANNING → READY → RUNNING) are verified in E2E smoke.

Status EPIC-09: Ready for development handoff.