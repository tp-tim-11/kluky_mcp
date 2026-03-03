from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool
    def add_record_if_not_exists(
        first_name: str,
        last_name: str,
        subject_name: str,
        what_i_am_fixing: str,
        repaired_with: list[str],
    ) -> str:
        """Shell tool placeholder for adding a new record if missing."""
        return (
            "NOT_IMPLEMENTED: "
            "add_record_if_not_exists("
            f"{first_name}, {last_name}, {subject_name}, "
            f"{what_i_am_fixing}, {repaired_with}"
            ")"
        )

    @mcp.tool
    def get_all_records_for_name(
        first_name: str,
        last_name: str,
    ) -> list[dict[str, object]]:
        """Shell tool placeholder for listing records by person name."""
        _ = (first_name, last_name)
        return []

    @mcp.tool
    def update_record(
        record_id: str,
        what_i_am_fixing: str,
        repaired_with: list[str],
    ) -> str:
        """Shell tool placeholder for updating an existing record."""
        return (
            "NOT_IMPLEMENTED: "
            f"update_record({record_id}, {what_i_am_fixing}, {repaired_with})"
        )
