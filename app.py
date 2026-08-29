from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
SOURCE_PATH = BASE_DIR / "mesbg.json"
CUSTOM_PATH = BASE_DIR / "lol27.json"
CONFIG_PATH = BASE_DIR / "new_factions_config.json"


def load_json(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_absolute():
        path = BASE_DIR / path

    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    if not path.is_absolute():
        path = BASE_DIR / path

    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def get_alignment_options(source: dict) -> list[str]:
    elements = source.get("elements", [])
    if elements:
        first = elements[0]
        if isinstance(first, dict):
            divisions = first.get("divisions", [])
            if divisions:
                return divisions

    return ["Kingdoms of Men", "Children of the Valar", "Remnants of Evil"]


def get_heroic_tier_options(source: dict) -> list[str]:
    tiers = source.get("data", {}).get("heroicTiers", [])
    names = []
    for tier in tiers:
        if isinstance(tier, dict):
            value = tier.get("name") or tier.get("title")
            if value:
                names.append(value)

    if not names:
        return ["Hero of Fortitude", "Minor Hero"]

    return names


def ensure_config_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = load_json(CONFIG_PATH)

    if "selected_faction_name" not in st.session_state:
        factions = st.session_state.config.get("customFactions", [])
        if factions:
            st.session_state.selected_faction_name = factions[0]["name"]


def get_selected_faction(config: dict):
    selected_name = st.session_state.get("selected_faction_name")
    for faction in config.get("customFactions", []):
        if faction.get("name") == selected_name:
            return faction
    return None


st.set_page_config(page_title="LOL27 Faction Editor", layout="wide")

source = load_json(SOURCE_PATH)
customs = load_json(CUSTOM_PATH)
ensure_config_state()
config = st.session_state.config
alignments = get_alignment_options(customs)
heroic_tiers = get_heroic_tier_options(source)
all_heroes = source.get("data", {}).get("heroes", [])
all_warriors = source.get("data", {}).get("warriors", [])

faction_names = [f.get("name", "Unnamed faction") for f in config.get("customFactions", [])]

st.title("Legions custom faction editor")

with st.sidebar:
    st.header("Factions")

    if st.button("New faction"):
        new_name = f"New Faction {len(config.get('customFactions', [])) + 1}"
        new_faction = {
            "name": new_name,
            "alignment": alignments[0],
            "additionalRules": [],
            "armyBonuses": [],
            "specialRules": [],
            "heroes": [],
            "warriors": [],
        }
        config.setdefault("customFactions", []).append(new_faction)
        st.session_state.selected_faction_name = new_name
        st.rerun()

    if faction_names:
        selected_faction_name = st.selectbox(
            "Select faction",
            faction_names,
            index=faction_names.index(st.session_state.get("selected_faction_name", faction_names[0]))
            if st.session_state.get("selected_faction_name") in faction_names
            else 0,
        )
        st.session_state.selected_faction_name = selected_faction_name

selected_faction = get_selected_faction(config)
if selected_faction is None:
    st.warning("No faction selected.")
    st.stop()

st.subheader(selected_faction["name"])

with st.form("faction_meta_form"):
    col1, col2 = st.columns(2)
    with col1:
        selected_faction["name"] = st.text_input("Faction name", value=selected_faction.get("name", ""))
    with col2:
        selected_faction["alignment"] = st.selectbox(
            "Alignment",
            alignments,
            index=alignments.index(selected_faction.get("alignment", alignments[0]))
            if selected_faction.get("alignment") in alignments else 0,
        )

    submitted = st.form_submit_button("Update faction details")
    if submitted:
        st.success("Faction details updated")

st.markdown("---")

hero_col, warrior_col = st.columns(2)

with hero_col:
    st.subheader("Heroes")
    if selected_faction.get("heroes"):
        for index, hero in enumerate(selected_faction.get("heroes", [])):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.write(hero["name"])
            with c2:
                st.write(hero.get("heroicTier", "Hero of Fortitude"))
            with c3:
                if st.button("Remove", key=f"remove_hero_{selected_faction['name']}_{index}"):
                    del selected_faction["heroes"][index]
                    st.rerun()
    else:
        st.caption("No heroes assigned")

    st.markdown("### Add hero")
    hero_search = st.text_input("Search heroes", key=f"hero_search_{selected_faction['name']}")
    filtered_heroes = [
        hero["name"]
        for hero in all_heroes
        if hero_search.lower() in hero["name"].lower()
    ]

    if filtered_heroes:
        selected_hero_name = st.selectbox("Choose hero", filtered_heroes, key=f"selected_hero_{selected_faction['name']}")
        hero_tier_choice = st.selectbox(
            "Heroic tier",
            heroic_tiers,
            index=heroic_tiers.index("Hero of Fortitude") if "Hero of Fortitude" in heroic_tiers else 0,
            key=f"hero_tier_{selected_faction['name']}",
        )

        if st.button("Add hero", key=f"add_hero_button_{selected_faction['name']}", disabled=False):
            if not any(item.get("name") == selected_hero_name for item in selected_faction.get("heroes", [])):
                selected_faction.setdefault("heroes", []).append(
                    {"name": selected_hero_name, "heroicTier": hero_tier_choice}
                )
                st.success(f"Added {selected_hero_name}")
                st.rerun()
            else:
                st.warning(f"{selected_hero_name} is already in this faction")
    else:
        st.info("No heroes match your search")
        st.button("Add hero", key=f"add_hero_button_{selected_faction['name']}", disabled=True)

with warrior_col:
    st.subheader("Warriors")
    if selected_faction.get("warriors"):
        for index, warrior in enumerate(selected_faction.get("warriors", [])):
            col_left, col_right = st.columns([4, 1])
            with col_left:
                warrior_display_name = warrior.get("duplicateAs") if isinstance(warrior, dict) else warrior
                if warrior_display_name is None:
                    warrior_display_name = warrior.get("name") if isinstance(warrior, dict) else warrior
                st.write(warrior_display_name)
            with col_right:
                if st.button("Remove", key=f"remove_warrior_{selected_faction['name']}_{index}"):
                    del selected_faction["warriors"][index]
                    st.rerun()
    else:
        st.caption("No warriors assigned")

    st.markdown("### Add warrior")
    warrior_search = st.text_input("Search warriors", key=f"warrior_search_{selected_faction['name']}")
    filtered_warriors = [
        warrior["name"]
        for warrior in all_warriors
        if warrior_search.lower() in warrior["name"].lower()
    ]

    if filtered_warriors:
        selected_warrior_name = st.selectbox("Choose warrior", filtered_warriors, key=f"selected_warrior_{selected_faction['name']}")
        warrior_rename = st.text_input(
            "Rename warrior (optional)",
            key=f"warrior_rename_{selected_faction['name']}",
            placeholder="Leave blank to keep the original name",
        )
        if st.button("Add warrior", key=f"add_warrior_button_{selected_faction['name']}", disabled=False):
            existing_warrior_names = [
                warrior.get("name") if isinstance(warrior, dict) else warrior
                for warrior in selected_faction.get("warriors", [])
            ]
            if selected_warrior_name not in existing_warrior_names:
                clean_rename = warrior_rename.strip() if warrior_rename else ""
                if clean_rename:
                    selected_faction.setdefault("warriors", []).append({
                        "name": selected_warrior_name,
                        "duplicateAs": clean_rename,
                    })
                    st.success(f"Added {selected_warrior_name} as {clean_rename}")
                else:
                    selected_faction.setdefault("warriors", []).append(selected_warrior_name)
                    st.success(f"Added {selected_warrior_name}")
                st.rerun()
            else:
                st.warning(f"{selected_warrior_name} is already in this faction")
    else:
        st.info("No warriors match your search")
        st.button("Add warrior", key=f"add_warrior_button_{selected_faction['name']}", disabled=True)

st.markdown("---")

if st.button("Save config to disk"):
    save_json(CONFIG_PATH, config)
    st.success(f"Saved config to {CONFIG_PATH.name}")
