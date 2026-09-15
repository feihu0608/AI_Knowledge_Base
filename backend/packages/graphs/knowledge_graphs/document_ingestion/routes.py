from .state import IngestionState


def route_after_validation(state: IngestionState) -> str:
    return "failed" if state.get("status") == "failed" else "parse_document"

