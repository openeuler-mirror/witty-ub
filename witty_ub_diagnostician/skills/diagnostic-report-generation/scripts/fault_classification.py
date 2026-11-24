"""Report classification and compatibility with the case matching taxonomy."""

from functools import lru_cache
import json
from pathlib import Path

REFERENCES = Path(__file__).resolve().parents[1] / "references"
CLASSIFICATION_FIELDS = ("domain", "component", "type")
PREVIOUS_FIELDS = ("fault_domain", "fault_component", "fault_type")
LEGACY_FIELDS = (*PREVIOUS_FIELDS, "first_level_label", "second_level_label")
LEGACY_USAGE = ("用户相关故障", "使用问题")
USAGE = ("业务故障", "误操作故障-KVCache使用问题")


@lru_cache(maxsize=1)
def fault_taxonomy():
    rows = json.loads((REFERENCES / "log_label.json").read_text(encoding="utf-8"))
    taxonomy = {}
    for row in rows:
        domain, component, fault_type = (row[field] for field in CLASSIFICATION_FIELDS)
        taxonomy.setdefault(domain, {}).setdefault(component, set()).add(fault_type)
    return taxonomy


def fault_types_for_case_label(label):
    return {fault_type for components in fault_taxonomy().values()
            for fault_type in components.get(label, ())}


def taxonomy_error(domain, component, fault_type):
    """Identify the first classification field outside its parent branch."""
    taxonomy = fault_taxonomy()
    if domain is not None and domain not in taxonomy:
        return "domain"
    components = taxonomy.get(domain, {})
    if component is not None and component not in components:
        return "component"
    if fault_type is not None and fault_type not in components.get(component, ()):
        return "type"
    return None


def classification_from_case_labels(component, fault_type):
    if not isinstance(component, str):
        return None, None, None
    if component == LEGACY_USAGE[0] and fault_type in (None, LEGACY_USAGE[1], USAGE[1]):
        component = USAGE[0]
        if fault_type is not None:
            fault_type = USAGE[1]
    matches = {domain: components[component] for domain, components in fault_taxonomy().items()
               if component in components}
    for domain, types in matches.items():
        if isinstance(fault_type, str) and fault_type in types:
            return domain, component, fault_type
    if len(matches) == 1:
        return next(iter(matches)), component, None
    return None, None, None


def write_classification(record, classification):
    record.update(zip(CLASSIFICATION_FIELDS, classification))
    for field in LEGACY_FIELDS:
        record.pop(field, None)


def migrate_classification(record, matched_class=None):
    """Project historical report fields through the current dictionary."""
    if "domain" in record:
        for field in LEGACY_FIELDS:
            record.pop(field, None)
        return
    if not any(field in record for field in LEGACY_FIELDS):
        return
    fault_type = record.get("fault_type", record.get("second_level_label"))
    component = record.get("first_level_label") or matched_class or record.get("fault_component")
    if fault_type == LEGACY_USAGE[1]:
        component, fault_type = USAGE
    for domain, components in fault_taxonomy().items():
        for candidate, types in components.items():
            if isinstance(fault_type, str) and fault_type in types:
                write_classification(record, (domain, candidate, fault_type))
                return
    classification = classification_from_case_labels(component, None)
    if classification[0] is None:
        previous_domain = record.get("fault_domain")
        if previous_domain in ("软件故障", "硬件故障"):
            classification = (previous_domain.removesuffix("故障"), None, None)
    write_classification(record, classification)


def primary_fault(data):
    faults = data.get("faults")
    if not isinstance(faults, list):
        return None
    faults = [fault for fault in faults if isinstance(fault, dict)]
    if not faults:
        return None
    summary = data.get("incident_summary")
    primary_id = summary.get("primary_fault_id") if isinstance(summary, dict) else None
    if primary_id:
        for fault in faults:
            if fault.get("id") == primary_id:
                return fault
    return next((fault for fault in faults if fault.get("role") == "primary"), faults[0])


def update_incident_classification(data):
    summary = data.get("incident_summary")
    fault = primary_fault(data)
    conclusion = fault.get("conclusion") if fault else data.get("conclusion")
    if isinstance(summary, dict) and isinstance(conclusion, dict):
        write_classification(summary, (conclusion.get(field) for field in CLASSIFICATION_FIELDS))
