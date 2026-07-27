"""DSL Parser - Parse YAML/JSON DSL into Scenario entities

Reference: ../docs/contracts/scenario-dsl.md
"""

import copy
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import yaml

from agenteval.core.exceptions import DSLParseError


@dataclass
class ScenarioEntity:
    """Parsed scenario entity (intermediate representation)"""

    external_id: str
    title: str
    description: str | None = None
    input_data: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    memory: dict = field(default_factory=dict)
    expected: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    judge_config: dict | None = None
    tags: list = field(default_factory=list)
    priority: int = 0
    metadata: dict = field(default_factory=dict)
    status: str = "active"


@dataclass
class DatasetMetadata:
    """Parsed dataset-level metadata"""

    name: str = ""
    version: str = ""
    description: str | None = None
    tags: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class DSLOutput:
    """Complete parse output"""

    dataset: DatasetMetadata
    scenarios: list[ScenarioEntity]


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts. Override wins. Lists are concatenated."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif isinstance(result.get(key), list) and isinstance(value, list):
            result[key] = result[key] + value
        else:
            result[key] = copy.deepcopy(value)
    return result


def expand_shorthand(scenario_raw: dict) -> dict:
    """Expand shorthand: top-level user_message -> input.user_message"""
    if "user_message" in scenario_raw and "input" not in scenario_raw:
        scenario_raw["input"] = {"user_message": scenario_raw.pop("user_message")}
    return scenario_raw


class DSLParser(ABC):
    """Abstract DSL parser"""

    @abstractmethod
    def parse(self, content: str) -> DSLOutput:
        """Parse DSL content into scenarios"""
        pass

    def _build_output(self, data: dict) -> DSLOutput:
        """Build DSLOutput from parsed data dict"""
        # Extract dataset metadata
        ds_raw = data.get("dataset", {})
        dataset_meta = DatasetMetadata(
            name=ds_raw.get("name", ""),
            version=ds_raw.get("version", ""),
            description=ds_raw.get("description"),
            tags=ds_raw.get("tags", []),
            metadata=ds_raw.get("metadata", {}),
        )

        # Extract defaults
        defaults = data.get("defaults", {})

        # Build scenarios
        scenarios = []
        for raw in data.get("scenarios", []):
            # Expand shorthand
            raw = expand_shorthand(raw)

            # Merge defaults
            merged_constraints = deep_merge(
                defaults.get("constraints", {}), raw.get("constraints", {})
            )
            merged_judge = None
            if defaults.get("judge_config") or raw.get("judge_config"):
                merged_judge = deep_merge(
                    defaults.get("judge_config", {}), raw.get("judge_config", {})
                )
            merged_memory = deep_merge(
                defaults.get("memory", {}), raw.get("memory", {})
            )
            # History: defaults prepended to scenario history
            default_history = defaults.get("history", [])
            scenario_history = default_history + raw.get("history", [])

            # Tags: union
            default_tags = defaults.get("tags", [])
            scenario_tags = list(set(default_tags + raw.get("tags", [])))

            # Parse input
            input_data = self._parse_input(raw)

            scenario = ScenarioEntity(
                external_id=raw.get("id", ""),
                title=raw.get("title", raw.get("id", "")),
                description=raw.get("description"),
                input_data=input_data,
                history=scenario_history,
                memory=merged_memory,
                expected=raw.get("expected", {}),
                constraints=merged_constraints,
                judge_config=merged_judge,
                tags=scenario_tags,
                priority=raw.get("priority", 0),
                metadata=raw.get("metadata", {}),
                status="active",
            )
            scenarios.append(scenario)

        return DSLOutput(dataset=dataset_meta, scenarios=scenarios)

    def _parse_input(self, raw: dict) -> dict:
        """Parse input field, handling shorthand. Returns empty dict if missing."""
        if "input" in raw:
            return raw["input"]
        if "user_message" in raw:
            return {"user_message": raw["user_message"], "context": raw.get("context", {})}
        # Return empty dict - validator will catch missing user_message
        return {}


class YAMLDSLParser(DSLParser):
    """YAML format DSL parser"""

    def parse(self, content: str) -> DSLOutput:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise DSLParseError(message=f"YAML parse error: {e}")

        if not isinstance(data, dict):
            raise DSLParseError(message="DSL root must be a YAML mapping")

        return self._build_output(data)


class JSONDSLParser(DSLParser):
    """JSON format DSL parser"""

    def parse(self, content: str) -> DSLOutput:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise DSLParseError(message=f"JSON parse error: {e}")

        if not isinstance(data, dict):
            raise DSLParseError(message="DSL root must be a JSON object")

        return self._build_output(data)


def get_parser(format: str) -> DSLParser:
    """Get parser by format"""
    parsers = {"yaml": YAMLDSLParser, "json": JSONDSLParser}
    if format not in parsers:
        raise ValueError(f"Unsupported format: {format}")
    return parsers[format]()
