from pathlib import Path
import json


def load_source(path: str | Path) -> dict:
    """
    Load the original Tabletop Admiral game file.

    Raises:
        FileNotFoundError
        json.JSONDecodeError
        ValueError
    """
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "data" not in data:
        raise ValueError(
            f"{path} does not appear to be a valid game file "
            "(missing top-level 'data' key)"
        )

    return data


def load_config(path: str | Path) -> dict:
    """
    Load custom faction configuration.

    Performs basic shape validation.
    """
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    if "customFactions" not in config:
        raise ValueError(
            "Config must contain a 'customFactions' array"
        )

    if not isinstance(config["customFactions"], list):
        raise ValueError(
            "'customFactions' must be a list"
        )

    return config


def validate_custom_factions(source: dict, config: dict):
    """Ensure every configured hero/warrior exists in the source file."""
    source_heroes = {hero["name"] for hero in source["data"].get("heroes", [])}
    source_warriors = {warrior["name"] for warrior in source["data"].get("warriors", [])}

    for faction in config["customFactions"]:
        for hero in faction.get("heroes", []):
            hero_name = hero.get("name")
            if hero_name is None:
                raise ValueError(f"Hero entry in faction '{faction.get('name')}' is missing a name")
            if hero_name not in source_heroes:
                raise ValueError(
                    f"Hero '{hero_name}' from faction '{faction.get('name')}' was not found in the source file"
                )

        for warrior_name in faction.get("warriors", []):
            if warrior_name not in source_warriors:
                raise ValueError(
                    f"Warrior '{warrior_name}' from faction '{faction.get('name')}' was not found in the source file"
                )

    return True


def save_output(output: dict, path: str | Path):
    """
    Save the custom Tabletop Admiral game file.

    Raises:
        FileNotFoundError
        json.JSONDecodeError
        ValueError
    """
    path = Path(path)

    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(output))

    return True


def build_hero_index(source: dict) -> dict:
    return {
        hero["name"]: hero
        for hero in source["data"]["heroes"]
    }


def build_warrior_index(source: dict) -> dict:
    return {
        warrior["name"]: warrior
        for warrior in source["data"]["warriors"]
    }


def build_gear_index(source: dict) -> dict:
    return {
        gear["name"]: gear
        for gear in source["data"]["gear"]
    }


def build_keyword_index(source: dict) -> dict:
    return {
        keyword["name"]: keyword
        for keyword in source["data"]["keywords"]
    }


def build_magic_index(source: dict) -> dict:
    return {
        keyword["name"]: keyword
        for keyword in source["data"]["magicalPowers"]
    }

def build_custom_index(source: dict, level) -> dict:
    return {
        custom["name"]: custom
        for custom in source["customisations"][level]
    }


def copy_skeleton(source: dict) -> dict:
    output = {
        k: v
        for k, v in source.items()
        if k != "data"
        }
    return output

def initialize_data(datafile, sourcefile):
    datafile["game"] = "Legion of Legends 2027"
    datafile["disallowMultipleFactions"] = "false"
    datafile["elements"][0]["divisions"] = ["Kingdoms of Men", "Children of the Valar", "Remnants of Evil"]
    datafile["data"] = {
        "factions": [],
        "heroicTiers": [],
        "heroes": [],
        "warriors": [],
        "siegeEquipment": [],
        "gear": [],
        "magicalPowers": [],
        "keywords": [],
        "armyBonuses": [],
    }

    datafile["data"]["heroicTiers"] = list(sourcefile["data"]["heroicTiers"])
    datafile["data"]["gear"] = list(sourcefile["data"]["gear"])
    datafile["data"]["keywords"] = list(sourcefile["data"]["keywords"])
    datafile["data"]["magicalPowers"] = list(sourcefile["data"]["magicalPowers"])

    return True


def add_heroes(datafile, custom_heroes, hero_index):
    for hero in custom_heroes:
        copied_hero = (hero_index[hero]).copy()
        copied_hero["factions"] = []
        datafile["data"]["heroes"].append(copied_hero)
    return True


def add_warriors(datafile, custom_warriors, warrior_index):
    for warrior in custom_warriors:
        copied_warrior = (warrior_index[warrior]).copy()
        copied_warrior["factions"] = []
        datafile["data"]["warriors"].append(copied_warrior)
    return True


def add_gear(datafile, imported_gear_names, gear_index):
    seen_gear = set()

    for gear_name in imported_gear_names:
        if gear_name in seen_gear:
            continue

        gear = gear_index.get(gear_name)
        if gear is None:
            continue

        datafile["data"].setdefault("gear", []).append(gear.copy())
        seen_gear.add(gear_name)

    return True


def add_keywords(datafile, imported_keyword_names, keyword_index):
    seen_keywords = set()

    for keyword_name in imported_keyword_names:
        if keyword_name in seen_keywords:
            continue

        keyword = keyword_index.get(keyword_name)
        if keyword is None:
            continue

        datafile["data"].setdefault("keywords", []).append(keyword.copy())
        seen_keywords.add(keyword_name)

    return True


def add_magical_powers(datafile, imported_magic_names, magic_index):
    seen_magicalpowers = set()

    for magic_name in imported_magic_names:
        if magic_name in seen_magicalpowers:
            continue

        magic = magic_index.get(magic_name)
        if magic is None:
            continue

        datafile["data"].setdefault("magicalPowers", []).append(magic.copy())
        seen_magicalpowers.add(magic_name)

    return True


def add_factions(datafile, custom_factions):
    for faction in custom_factions:
        faction_data = {
            "name": faction["name"],
            "alignment": faction["alignment"],
            "additionalRules": faction.get("additionalRules", []),
            "armyBonuses": faction.get("armyBonuses", []),
            "specialRules": faction.get("specialRules", []),
        }

        datafile["data"]["factions"].append(faction_data)

    return True


def attach_warrior_factions(datafile, custom_factions):
    warrior_lookup = {
        warrior["name"]: warrior
        for warrior in datafile["data"]["warriors"]
    }

    for faction in custom_factions:
        faction_name = faction["name"]

        for warrior_name in faction.get("warriors", []):
            warrior = warrior_lookup.get(warrior_name)
            if warrior is None:
                continue

            warrior.setdefault("factions", []).append(faction_name)

    return True


def attach_hero_factions(datafile, custom_factions):
    hero_lookup = {
        hero["name"]: hero
        for hero in datafile["data"]["heroes"]
    }

    for faction in custom_factions:
        faction_name = faction["name"]

        for hero in faction.get("heroes", []):
            hero_name = hero["name"]
            hero_obj = hero_lookup.get(hero_name)
            if hero_obj is None:
                continue

            hero_obj.setdefault("factions", []).append({
                "name": faction_name,
                "heroicTier": hero.get("heroicTier")
            })

    return True


def attach_factions(output, conf):
    add_factions(output, conf["customFactions"])
    attach_warrior_factions(output, conf["customFactions"])
    attach_hero_factions(output, conf["customFactions"])
    return True

def customise_profiles(output,conf):
    for level in ['heroes','warriors']:
        custom_index = build_custom_index(conf,level)
        lookup = {
            x["name"]: x
            for x in output["data"]["heroes"]
        }

        for thing in custom_index:
            if thing is not None and 'rename' in custom_index.get(thing):
                thing_name = custom_index.get(thing).get("name")
                thing_rename = custom_index.get(thing).get("rename")
                thing_obj = lookup.get(thing_name)
                if thing_obj is None:
                    continue

                thing_obj["name"] = thing_rename
    return True


def buid_custom_factions_file(source_file, config_file, output_file):
    conf = load_config(config_file)
    src = load_source(source_file)
    validate_custom_factions(src, conf)
    hero_index = build_hero_index(src)
    warrior_index = build_warrior_index(src)
    gear_index = build_gear_index(src)
    keyword_index = build_keyword_index(src)
    magic_index = build_magic_index(src)

    output = copy_skeleton(src)
    initialize_data(output,src)

    #get a list of heroes and warriors used in the custom list
    heroes_in_custom = {
        hero["name"]
        for faction in conf["customFactions"]
        for hero in faction.get("heroes", [])
    }

    warriors_in_custom = {
        warrior
        for faction in conf["customFactions"]
        for warrior in faction.get("warriors", [])
    }

    add_heroes(output, heroes_in_custom, hero_index)
    add_warriors(output, warriors_in_custom, warrior_index)    
    attach_factions(output, conf)
    customise_profiles(output=output,conf=conf)

    save_output(output, output_file)

if __name__ == "__main__":
    buid_custom_factions_file(
        "mesbg.json",
        "new_factions_config.json",
        "lol27.json",
    )