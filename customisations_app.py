from __future__ import annotations

import json
import subprocess
import sys
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


def insert_object_rows(insert_object: dict[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(insert_object, dict):
        return [{"key": "", "value": ""}]
    return [
        {"key": str(key), "value": json.dumps(value, ensure_ascii=False)}
        for key, value in insert_object.items()
    ] or [{"key": "", "value": ""}]


def rows_to_insert_object(rows: list[dict[str, Any]]) -> dict[str, Any]:
    insert_object: dict[str, Any] = {}
    for row in rows:
        key = str(row.get("key", "")).strip()
        value = str(row.get("value", "")).strip()
        if not key:
            if value:
                raise ValueError("Object keys cannot be empty")
            continue
        insert_object[key] = parse_value(value)
    if not insert_object:
        raise ValueError("Add at least one key/value pair")
    return insert_object


def insert_object_groups(customisations: dict[str, Any]) -> list[dict[str, Any]]:
    groups = customisations.get("insertObjects", [])
    if not isinstance(groups, list):
        return []
    return [group for group in groups if isinstance(group, dict)]


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


def alignment_options(config: dict[str, Any]) -> list[str]:
    values = config.get("alignments", [])
    return values if isinstance(values, list) and values else [
        "Kingdoms of Men",
        "Children of the Valar",
        "Remnants of Evil",
    ]


def heroic_tier_options(profile_data: dict[str, Any]) -> list[str]:
    tiers = profile_data.get("data", {}).get("heroicTiers", [])
    names = [
        tier.get("name") or tier.get("title")
        for tier in tiers
        if isinstance(tier, dict)
    ]
    names = [name for name in names if name]
    return names or ["Hero of Fortitude", "Minor Hero"]


def source_unit_names(profile_data: dict[str, Any], level: str) -> list[str]:
    profiles = profile_data.get("data", {}).get(level, [])
    return [
        profile.get("name")
        for profile in profiles
        if isinstance(profile, dict) and profile.get("name")
    ]


def new_faction(name: str, alignment: str) -> dict[str, Any]:
    return {
        "name": name,
        "alignment": alignment,
        "additionalRules": [],
        "armyBonuses": [],
        "specialRules": [],
        "heroes": [],
        "warriors": [],
    }


def render_faction_editor(
    config: dict[str, Any],
    faction: dict[str, Any],
    profile_data: dict[str, Any],
) -> None:
    st.subheader(faction.get("name", "Faction"))
    alignments = alignment_options(config)

    with st.form("faction_meta_form"):
        faction_name = st.text_input("Faction name", value=faction.get("name", ""))
        faction_alignment = st.selectbox(
            "Alignment",
            alignments,
            index=alignments.index(faction.get("alignment"))
            if faction.get("alignment") in alignments else 0,
        )
        if st.form_submit_button("Save faction details"):
            faction_name = faction_name.strip()
            if not faction_name:
                st.error("Faction name is required")
            elif any(
                other is not faction and other.get("name") == faction_name
                for other in config.get("customFactions", [])
            ):
                st.error(f"A faction named {faction_name} already exists")
            else:
                faction["name"] = faction_name
                faction["alignment"] = faction_alignment
                st.session_state.selected_faction_name = faction_name
                save_json(CONFIG_PATH, config)
                st.success(f"Saved faction details for {faction_name}")

    hero_names = source_unit_names(profile_data, "heroes")
    warrior_names = source_unit_names(profile_data, "warriors")
    tiers = heroic_tier_options(profile_data)
    hero_col, warrior_col = st.columns(2)

    with hero_col:
        st.subheader("Heroes")
        heroes = faction.setdefault("heroes", [])
        if heroes:
            for index, hero in enumerate(heroes):
                hero_name = hero.get("name", "Unnamed hero") if isinstance(hero, dict) else str(hero)
                hero_tier = hero.get("heroicTier", "Hero of Fortitude") if isinstance(hero, dict) else ""
                row_left, row_middle, row_right = st.columns([3, 2, 1])
                row_left.write(hero_name)
                row_middle.write(hero_tier)
                if row_right.button("Remove", key=f"remove_hero_{faction.get('name')}_{index}"):
                    heroes.pop(index)
                    save_json(CONFIG_PATH, config)
                    st.rerun()
        else:
            st.caption("No heroes assigned")

        hero_search = st.text_input("Search heroes", key=f"hero_search_{faction.get('name')}")
        filtered_heroes = [name for name in hero_names if hero_search.lower() in name.lower()]
        if filtered_heroes:
            selected_hero = st.selectbox("Choose hero", filtered_heroes, key=f"selected_hero_{faction.get('name')}")
            selected_tier = st.selectbox(
                "Heroic tier",
                tiers,
                index=tiers.index("Hero of Fortitude") if "Hero of Fortitude" in tiers else 0,
                key=f"hero_tier_{faction.get('name')}",
            )
            if st.button("Add hero", key=f"add_hero_{faction.get('name')}"):
                if any(
                    item.get("name") == selected_hero
                    for item in heroes
                    if isinstance(item, dict)
                ):
                    st.warning(f"{selected_hero} is already in this faction")
                else:
                    heroes.append({"name": selected_hero, "heroicTier": selected_tier})
                    save_json(CONFIG_PATH, config)
                    st.rerun()
        else:
            st.info("No heroes match your search")

    with warrior_col:
        st.subheader("Warriors")
        warriors = faction.setdefault("warriors", [])
        if warriors:
            for index, warrior in enumerate(warriors):
                warrior_name = (
                    warrior.get("duplicateAs") or warrior.get("name")
                    if isinstance(warrior, dict)
                    else str(warrior)
                )
                row_left, row_right = st.columns([4, 1])
                row_left.write(warrior_name)
                if row_right.button("Remove", key=f"remove_warrior_{faction.get('name')}_{index}"):
                    warriors.pop(index)
                    save_json(CONFIG_PATH, config)
                    st.rerun()
        else:
            st.caption("No warriors assigned")

        warrior_search = st.text_input("Search warriors", key=f"warrior_search_{faction.get('name')}")
        filtered_warriors = [name for name in warrior_names if warrior_search.lower() in name.lower()]
        if filtered_warriors:
            selected_warrior = st.selectbox(
                "Choose warrior",
                filtered_warriors,
                key=f"selected_warrior_{faction.get('name')}",
            )
            warrior_rename = st.text_input(
                "Rename warrior (optional)",
                key=f"warrior_rename_{faction.get('name')}",
                placeholder="Leave blank to keep the original name",
            )
            if st.button("Add warrior", key=f"add_warrior_{faction.get('name')}"):
                existing_names = [
                    item.get("name") if isinstance(item, dict) else item
                    for item in warriors
                ]
                if selected_warrior in existing_names:
                    st.warning(f"{selected_warrior} is already in this faction")
                else:
                    clean_rename = warrior_rename.strip()
                    warriors.append(
                        {
                            "name": selected_warrior,
                            "duplicateAs": clean_rename,
                        }
                        if clean_rename else selected_warrior
                    )
                    save_json(CONFIG_PATH, config)
                    st.rerun()
        else:
            st.info("No warriors match your search")


def render_insert_objects_editor(customisations: dict[str, Any]) -> None:
    st.subheader("Insert objects")
    st.caption("Create or edit objects in the keywords and gear categories. Values accept JSON or plain text.")

    groups = insert_object_groups(customisations)
    destinations = sorted({str(group.get("destination", "")) for group in groups if group.get("destination")})
    destination_options = sorted(set(destinations) | {"keywords", "gear"})
    selected_destination = st.selectbox(
        "Category",
        destination_options,
        key="insert_objects_destination",
    )

    selected_group = next(
        (
            group for group in groups
            if group.get("destination") == selected_destination
        ),
        None,
    )
    objects = selected_group.get("objects", []) if selected_group else []
    if not isinstance(objects, list):
        objects = []
    objects = [obj for obj in objects if isinstance(obj, dict)]

    object_labels = [
        f"{index + 1}: {obj.get('name', 'Unnamed object')}"
        for index, obj in enumerate(objects)
    ]
    selected_object = st.selectbox(
        "Object",
        ["New object", *object_labels],
        key=f"insert_objects_selection_{selected_destination}",
    )
    selected_index = object_labels.index(selected_object) if selected_object in object_labels else None
    current_object = objects[selected_index] if selected_index is not None else None

    object_rows = st.data_editor(
        insert_object_rows(current_object),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "key": st.column_config.TextColumn("Key", required=True),
            "value": st.column_config.TextColumn("Value (JSON or text)", required=True),
        },
        key=f"insert_object_editor_{selected_destination}_{selected_object}",
    )
    operation = st.selectbox(
        "Action",
        ["Create new", "Update selected", "Delete selected"],
        index=1 if selected_index is not None else 0,
        key=f"insert_objects_operation_{selected_destination}_{selected_object}",
    )

    if st.button("Save insert object", type="primary", key="save_insert_object"):

        try:
            if operation == "Delete selected":
                if selected_index is None:
                    raise ValueError("Select an existing object to delete")
                objects.pop(selected_index)
            else:
                new_object = rows_to_insert_object(object_rows)
                if operation == "Update selected":
                    if selected_index is None:
                        raise ValueError("Select an existing object to update")
                    objects[selected_index] = new_object
                else:
                    objects.append(new_object)

            target_group = selected_group
            if target_group is None:
                target_group = {"destination": selected_destination, "objects": []}
                groups.append(target_group)
            target_group["objects"] = objects
            customisations["insertObjects"] = groups
            save_json(CONFIG_PATH, config)
            st.success(f"Saved {selected_destination} insert objects")
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            st.error(str(error))


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
            rows.append({"Name": name, "Points": "Wargear"})

    for item in profile.get("options", []):
        if isinstance(item, dict):
            name = item.get("name") or item.get("text") or ""
            points = item.get("points")
        else:
            name = str(item)
            points = None
        if name:
            rows.append({"Name": name, "Points": points})
            
    for item in profile.get("specialRules", []):
        if isinstance(item, dict):
            name = item.get("name") or item.get("text") or ""
        else:
            name = str(item)
        if name:
            rows.append({"Name": name, "Points": "Special Rule"})

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
    alignments = alignment_options(config)
    if st.button("New faction", key="new_faction"):
        faction_number = len(factions) + 1
        faction_name = f"New Faction {faction_number}"
        while any(faction.get("name") == faction_name for faction in factions):
            faction_number += 1
            faction_name = f"New Faction {faction_number}"
        factions.append(new_faction(faction_name, alignments[0]))
        st.session_state.selected_faction_name = faction_name
        save_json(CONFIG_PATH, config)
        st.rerun()

    if st.button("Build Legions output", key="build_legions"):
        try:
            build_result = subprocess.run(
                [sys.executable, str(BASE_DIR / "build_legions.py")],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            st.error("Build timed out after 120 seconds")
        except OSError as error:
            st.error(f"Could not start build: {error}")
        else:
            if build_result.returncode == 0:
                st.success("Legions output built successfully")
            else:
                st.error(f"Build failed with exit code {build_result.returncode}")
            build_output = "\n".join(
                output for output in (build_result.stdout, build_result.stderr) if output
            ).strip()
            if build_output:
                with st.expander("Build output"):
                    st.code(build_output)

    faction_names = [faction.get("name", "Unnamed faction") for faction in factions]
    if not faction_names:
        st.warning("No custom factions found.")
        st.stop()
    if st.session_state.get("selected_faction_name") not in faction_names:
        st.session_state.selected_faction_name = faction_names[0]
    selected_faction_name = st.selectbox(
        "Select faction",
        faction_names,
        index=faction_names.index(st.session_state.selected_faction_name),
        key="selected_faction_name",
    )

selected_faction = next(
    faction for faction in factions
    if faction.get("name") == selected_faction_name
)

st.title("Legions customisation editor")

faction_tab, profile_tab, insert_objects_tab = st.tabs(
    ["Faction editor", "Profile customisations", "Insert objects"]
)
with faction_tab:
    render_faction_editor(config, selected_faction, st.session_state.mesbg_profile_data)

with insert_objects_tab:
    render_insert_objects_editor(customisations)

with profile_tab:
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
        st.caption("Wargear, options and special rules")
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