.PHONY: test test-unit test-golden lint contract-validate contract-docs ci

# Run all unit tests
test:
	python -m pytest tests/ -v

# Run only unit tests (fast, no LLM)
test-unit:
	python -m pytest tests/unit/ -v

# Run golden scenario tests
test-golden:
	python -m pytest tests/unit/test_golden_scenarios.py -v

# Run linter
lint:
	python -m ruff check src/ tests/

# Validate contracts via agent-contracts registry
contract-validate:
	python -c "\
from splitmind_ai.app.graph import register_all_nodes, reset_registry_safe; \
from agent_contracts import get_node_registry; \
from splitmind_ai.eval.observability import reset_registry_safe; \
reset_registry_safe(); register_all_nodes(); \
registry = get_node_registry(); \
print(f'Registered {len(registry.get_all_nodes())} nodes'); \
print('Contract validation: OK')"

# Generate architecture docs
contract-docs:
	python -c "\
from splitmind_ai.eval.observability import generate_contract_docs; \
from pathlib import Path; \
generate_contract_docs(Path('docs/generated'))"

# Full CI pipeline (no LLM required)
ci: lint test contract-validate contract-docs
	@echo "CI pipeline complete"
