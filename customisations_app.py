from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "new_factions_config.json"
MESBG_PATH = BASE_DIR / "mesbg.json"
ACTION_OPTIONS = ["append", "remove", "update", "delete", "rename"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def find_profile_points(profile_data: dict[str, Any], level: str, profile_name: str) -> Any:
    profiles = profile_data.get("data", {}).get(level, [])
    profile = next(
        (profile for profile in profiles if profile.get("name") == profile_name),
        None,
    )
    return profile.get("points") if profile else None


def source_profile_name(faction: dict[str, Any], level: str, profile_name: str) -> str:
    profile = next(
        (
            profile for profile in faction.get(level, [])
            if effective_profile_name(profile) == profile_name
        ),
        None,
    )
    if isinstance(profile, dict):
        return profile.get("name", profile_name)
    return profile_name


def effective_profile_name(profile: Any) -> str | None:
    if isinstance(profile, str):
        return profile
    if isinstance(profile, dict):
        return profile.get("duplicateAs") or profile.get("name")
    return None


def faction_profiles(faction: dict[str, Any], level: str) -> list[str]:
    # for profile in faction.get(level,[]):
    #     print(profile)
    #     print(effective_profile_name(profile))
    #     break
    names = [
        effective_profile_name(profile)
        for profile in faction.get(level, [])
    ]
    return [name for name in names if name]


def find_customisation(customisations: list[dict[str, Any]], profile_name: str) -> dict[str, Any] | None:
    return next(
        (custom for custom in customisations if custom.get("name") == profile_name),
        None,
    )


def add_customisation(customisations: list[dict[str, Any]], profile_name: str) -> dict[str, Any]:
    customisation = find_customisation(customisations, profile_name)
    if customisation is None:
        customisation = {"name": profile_name}
        customisations.append(customisation)
    return customisation


def customisation_rows(customisation: dict[str, Any] | None) -> list[dict[str, str]]:
    if customisation is None:
        return []

    rows = []
    for action in ACTION_OPTIONS:
        instructions = customisation.get(action)
        if instructions is None:
            continue

        if action == "rename":
            rows.append({"action": action, "field": "name", "value": json.dumps(instructions, ensure_ascii=False)})
            continue

        if action == "delete":
            for field in instructions if isinstance(instructions, list) else []:
                rows.append({"action": action, "field": str(field), "value": ""})
            continue

        if isinstance(instructions, dict):
            for field, value in instructions.items():
                rows.append({
                    "action": action,
                    "field": str(field),
                    "value": json.dumps(value, ensure_ascii=False),
                })
    return rows


def parse_value(value: str) -> Any:
    value = value.strip()
    if not value:
        raise ValueError("Value is required for this action")
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def rows_to_customisation(profile_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    customisation: dict[str, Any] = {"name": profile_name}

    for row in rows:
        action = str(row.get("action", "")).strip()
        field = str(row.get("field", "")).strip()
        value = str(row.get("value", "")).strip()

        if action not in ACTION_OPTIONS:
            raise ValueError(f"Unknown action: {action}")
        if action == "rename":
            field = "name"
        elif not field:
            raise ValueError(f"Target field is required for {action}")

        if action == "delete":
            customisation.setdefault("delete", []).append(field)
        elif action == "rename":
            customisation["rename"] = parse_value(value)
        else:
            parsed_value = parse_value(value)
            customisation.setdefault(action, {})[field] = parsed_value

    return customisation


LIST_FIELD_OPTIONS = ["options", "wargear", "specialRules"]


def list_builder_columns(field_name: str) -> list[str]:
    if field_name == "specialRules":
        return ["name", "description"]
    return ["name", "points"]


def materialise_list_row(row: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    item_name = str(row.get("name", "")).strip()
    if not item_name:
        return None

    item: dict[str, Any] = {"name": item_name}

    if field_name != "specialRules":
        points_value = row.get("points")
        if points_value not in (None, ""):
            try:
                item["points"] = int(points_value)
            except (TypeError, ValueError):
                try:
                    item["points"] = float(points_value)
                except (TypeError, ValueError):
                    item["points"] = str(points_value).strip()

    description = str(row.get("description", "")).strip()
    if description:
        item["description"] = description

    return item


def build_list_customisation_value(field_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        item = materialise_list_row(row, field_name)
        if item is not None:
            items.append(item)
    return items


def profile_equipment_rows(profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(profile, dict):
        return []

    rows: list[dict[str, Any]] = []

    for item in profile.get("wargear", []):
        if isinstance(item, dict):
            name = item.get("name") or item.get("text") or ""
        else:
            name = str(item)
        if name:
            rows.append({"Name": name, "Points": None})

    for item in profile.get("options", []):
        if isinstance(item, dict):
            name = item.get("name") or item.get("text") or ""
            points = item.get("points")
        else:
            name = str(item)
            points = None
        if name:
            rows.append({"Name": name, "Points": points})

    return rows


def ensure_state() -> None:
    if "customisation_config" not in st.session_state:
        st.session_state.customisation_config = load_json(CONFIG_PATH)
    if "mesbg_profile_data" not in st.session_state:
        st.session_state.mesbg_profile_data = load_json(MESBG_PATH)


st.set_page_config(page_title="LOL27 Customisation Editor", layout="wide")
ensure_state()
config = st.session_state.customisation_config
customisations = config.setdefault("customisations", {})

with st.sidebar:
    st.header("Faction")
    factions = config.get("customFactions", [])
    faction_names = [faction.get("name", "Unnamed faction") for faction in factions]
    if not faction_names:
        st.warning("No custom factions found.")
        st.stop()
    selected_faction_name = st.selectbox("Select faction", faction_names)

selected_faction = next(
    faction for faction in factions
    if faction.get("name") == selected_faction_name
)

st.title("Legions customisation editor")

# st.subheader("1. Select unit type")
level_label = st.selectbox("Unit type", ["Heroes", "Warriors"])
level = level_label.lower()
level_customisations = customisations.setdefault(level, [])

# st.subheader("2. Select profile")
profile_names = faction_profiles(selected_faction, level)
if not profile_names:
    st.warning(f"No {level} profiles found in this faction.")
    st.stop()

selected_profile = st.selectbox("Profile", profile_names)
existing = find_customisation(level_customisations, selected_profile)

# st.subheader("3. Add customisation")

quick_list_field = st.selectbox(
    "Quick list field",
    ["-- manual JSON --", *LIST_FIELD_OPTIONS],
    index=0,
    key=f"quick_list_field_{level}_{selected_profile}",
)
quick_list_action = st.selectbox(
    "Quick list action",
    ["update", "append", "remove"],
    index=0,
    key=f"quick_list_action_{level}_{selected_profile}",
)

quick_list_rows: list[dict[str, Any]] = []
if quick_list_field != "-- manual JSON --":
    field_columns = list_builder_columns(quick_list_field)
    current_items: list[dict[str, Any]] = []

    for custom in level_customisations:
        if custom.get("name") != selected_profile:
            continue
        for action_name in ("update", "append"):
            payload = custom.get(action_name, {})
            if not isinstance(payload, dict):
                continue
            for item in payload.get(quick_list_field, []):
                if isinstance(item, dict):
                    current_items.append(item)

    if quick_list_action == "remove":
        remove_names = sorted({item.get("name") for item in current_items if isinstance(item, dict) and item.get("name")})
        selected_remove_names = st.multiselect(
            f"Remove from {quick_list_field}",
            remove_names,
            key=f"quick_remove_{level}_{selected_profile}_{quick_list_field}",
        )
        quick_list_rows = [{"name": name} for name in selected_remove_names]
    else:
        default_rows = []
        if current_items:
            default_rows = [
                {column: item.get(column, "") for column in field_columns if column in item}
                for item in current_items
            ]
        else:
            default_rows = [{column: "" for column in field_columns}]

        quick_list_rows = st.data_editor(
            default_rows,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Name", required=True),
                "points": st.column_config.NumberColumn("Points", min_value=0, step=1),
                "description": st.column_config.TextColumn("Description"),
            },
            key=f"quick_list_editor_{level}_{selected_profile}_{quick_list_field}",
        )

    if quick_list_rows:
        st.caption(f"Generated JSON: {json.dumps(build_list_customisation_value(quick_list_field, quick_list_rows), ensure_ascii=False)}")

st.caption("Enter text or numbers directly, or use JSON for lists and objects, for example `Shield`, `60`, `[\"Bow\"]`, or `{\"points\": 60}`.")

rows = customisation_rows(existing)
if not rows:
    rows = [{"action": "append", "field": "", "value": ""}]
edited_rows = st.data_editor(
    rows,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "action": st.column_config.SelectboxColumn("Action", options=ACTION_OPTIONS, required=True),
        "field": st.column_config.TextColumn("Target field"),
        "value": st.column_config.TextColumn("Value (JSON)"),
    },
    key=f"customisation_rows_{level}_{selected_profile}",
)

profile_name = source_profile_name(selected_faction, level, selected_profile)
profile_points = find_profile_points(
    st.session_state.mesbg_profile_data,
    level,
    profile_name,
)
if profile_points is None:
    st.caption("LOL27 points: not available")
else:
    st.caption(f"LOL27 points: {profile_points}")

source_profile = next(
    (
        profile
        for profile in st.session_state.mesbg_profile_data.get("data", {}).get(level, [])
        if profile.get("name") == profile_name
    ),
    None,
)
profile_equipment = profile_equipment_rows(source_profile)
if profile_equipment:
    st.caption("Wargear and options")
    st.table(profile_equipment)

for row in edited_rows:
    if row.get("action") == "rename":
        row["field"] = "name"

if st.button("Save customisation", type="primary"):
    try:
        updated = rows_to_customisation(selected_profile, edited_rows)
        if quick_list_field != "-- manual JSON --":
            if quick_list_action == "remove":
                selected_names = [row.get("name") for row in quick_list_rows if isinstance(row, dict) and row.get("name")]
                if selected_names:
                    updated.setdefault("remove", {})[quick_list_field] = selected_names
            elif quick_list_action in {"update", "append"}:
                list_value = build_list_customisation_value(quick_list_field, quick_list_rows)
                if list_value or quick_list_action == "update":
                    updated.setdefault(quick_list_action, {})[quick_list_field] = list_value
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        st.error(str(error))
    else:
        level_customisations[:] = [
            custom for custom in level_customisations
            if custom.get("name") != selected_profile
        ]
        add_customisation(level_customisations, selected_profile).update(updated)
        save_json(CONFIG_PATH, config)
        st.success(f"Saved customisation for {selected_profile}")