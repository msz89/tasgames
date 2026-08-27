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


def extract_hero_duplications(conf: dict) -> dict:
    """Extract hero duplication mappings from faction configs.
    
    Returns:
        dict: {original_name: duplicate_as_name, ...}
    """
    duplications = {}
    for faction in conf.get("customFactions", []):
        for hero_config in faction.get("heroes", []):
            if isinstance(hero_config, dict) and "duplicateAs" in hero_config:
                hero_name = hero_config.get("name")
                duplicate_as = hero_config.get("duplicateAs")
                if hero_name and duplicate_as:
                    duplications[hero_name] = duplicate_as
    return duplications


def extract_warrior_duplications(conf: dict) -> dict:
    """Extract warrior duplication mappings from faction configs.
    
    Returns:
        dict: {original_name: duplicate_as_name, ...}
    """
    duplications = {}
    for faction in conf.get("customFactions", []):
        for warrior_config in faction.get("warriors", []):
            if isinstance(warrior_config, dict) and "duplicateAs" in warrior_config:
                warrior_name = warrior_config.get("name")
                duplicate_as = warrior_config.get("duplicateAs")
                if warrior_name and duplicate_as:
                    duplications[warrior_name] = duplicate_as
    return duplications


def normalize_faction_configs(conf: dict):
    """Remove duplication config from faction hero/warrior configs after extraction.
    
    Modifies conf in place to remove the duplicateAs property from objects,
    but keeps the full hero/warrior objects intact for other functions.
    """
    for faction in conf.get("customFactions", []):
        # Clean duplicateAs from heroes but keep full objects
        heroes = faction.get("heroes", [])
        for hero in heroes:
            if isinstance(hero, dict) and "duplicateAs" in hero:
                del hero["duplicateAs"]
        
        # Change warrior object to just the name
        warriors = faction.get("warriors", [])
        for i, warrior in enumerate(warriors):
            if isinstance(warrior, dict) and "duplicateAs" in warrior:
                faction["warriors"][i] = warrior.get("name")


def validate_custom_factions(source: dict, config: dict):
    """Ensure every configured hero/warrior exists in the source file."""
    source_heroes = {hero["name"] for hero in source["data"].get("heroes", [])}
    source_warriors = {warrior["name"] for warrior in source["data"].get("warriors", [])}

    for faction in config["customFactions"]:
        for hero_config in faction.get("heroes", []):
            # Handle simple string format or object format
            if isinstance(hero_config, str):
                hero_name = hero_config
            else:
                hero_name = hero_config.get("name")
            
            if hero_name is None:
                raise ValueError(f"Hero entry in faction '{faction.get('name')}' is missing a name")
            if hero_name not in source_heroes:
                raise ValueError(
                    f"Hero '{hero_name}' from faction '{faction.get('name')}' was not found in the source file"
                )

        for warrior_config in faction.get("warriors", []):
            # Handle simple string format or object format
            if isinstance(warrior_config, str):
                warrior_name = warrior_config
            else:
                warrior_name = warrior_config.get("name")
            
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
        json.dump(output, f, indent=4, ensure_ascii=False)
     
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
        if k not in ["data","campaigns","campaignPacks"]
        }
    return output

# def set_gamefile_property():

def initialize_data(datafile, sourcefile, conf):

    for prop in conf["gameConfig"]:
        datafile[prop] = conf['gameConfig'].get(prop)

    #this bit would be harder to do pythonic
    datafile["elements"][0]["divisions"] = conf["alignments"]

    ## is this required if we set_default
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

    # dupe the subsections
    for section in ["heroicTiers","gear","keywords","magicalPowers"]:
        datafile["data"][section] = list(sourcefile.get("data").get(section))

    return True


def add_heroes(datafile, profiles_to_add, hero_index):
    """Add heroes to datafile.
    
    Args:
        profiles_to_add: Set of (original_name, output_name) tuples
    """
    for original_name, output_name in profiles_to_add:
        copied_hero = hero_index[original_name].copy()
        copied_hero["name"] = output_name
        copied_hero["factions"] = []
        datafile["data"]["heroes"].append(copied_hero)
    return True


def add_warriors(datafile, profiles_to_add, warrior_index):
    """Add warriors to datafile.
    
    Args:
        profiles_to_add: Set of (original_name, output_name) tuples
    """
    for original_name, output_name in profiles_to_add:
        copied_warrior = warrior_index[original_name].copy()
        copied_warrior["name"] = output_name
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


def attach_faction_alliances(datafile, customfactions):
    faction_lookup = {
        faction["name"]: faction
        for faction in datafile["data"]["factions"]
    }
    allies_list = {
        f["name"]: f["alignment"]
        for f in customfactions
        }
 
    for faction in customfactions:
        faction_name = faction["name"]
        faction_allies = [
            f 
            for f in allies_list
            if faction_name != f
            and allies_list[f] == allies_list[faction_name]
        ]
        faction_lookup[faction_name].setdefault("primaryAllies",[]).extend(faction_allies)
        faction_lookup[faction_name].setdefault("secondaryAllies",[])


    return True


def attach_warrior_factions(datafile, custom_factions):
    warrior_lookup = {
        warrior["name"]: warrior
        for warrior in datafile["data"]["warriors"]
    }

    for faction in custom_factions:
        faction_name = faction["name"]

        for warrior_config in faction.get("warriors", []):
            # Get the original name and output name
            if isinstance(warrior_config, str):
                original_name = warrior_config
                output_name = warrior_config
            else:
                original_name = warrior_config.get("name")
                output_name = warrior_config.get("duplicateAs", original_name)
            
            warrior = warrior_lookup.get(output_name)
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

        for hero_config in faction.get("heroes", []):
            # Get the original name, output name, and heroic tier
            if isinstance(hero_config, str):
                original_name = hero_config
                output_name = hero_config
                heroic_tier = None
            else:
                original_name = hero_config.get("name")
                output_name = hero_config.get("duplicateAs", original_name)
                heroic_tier = hero_config.get("heroicTier")
            
            hero_obj = hero_lookup.get(output_name)
            if hero_obj is None:
                continue

            hero_obj.setdefault("factions", []).append({
                "name": faction_name,
                "heroicTier": heroic_tier
            })

    return True

def attach_factions_with_mapping(output, conf, hero_faction_mapping, warrior_faction_mapping):
    """Attach factions to profiles using pre-built mappings."""
    # First add the faction definitions
    add_factions(output, conf["customFactions"])
    attach_faction_alliances(output,conf["customFactions"])
    
    # Attach hero factions
    hero_lookup = {
        hero["name"]: hero
        for hero in output["data"]["heroes"]
    }

    # Elites labels
    elite_heroes = [
        hero for hero in conf["customisations"]["appendData"]["heroes"]
        ]
    elite_warriors = [
        warrior for warrior in conf["customisations"]["appendData"]["warriors"]
        ]
    tag = conf["customisations"]["appendData"]["tag"]
    label = conf["customisations"]["appendData"]["value"]

    for output_name, faction_list in hero_faction_mapping.items():
        hero = hero_lookup.get(output_name)

        if output_name in elite_heroes:
            hero.setdefault(tag,[]).append(label)

        if hero is None:
            continue
        
        hero["factions"] = faction_list
    
    # Attach warrior factions
    warrior_lookup = {
        warrior["name"]: warrior
        for warrior in output["data"]["warriors"]
    }
    
    for output_name, faction_list in warrior_faction_mapping.items():
        warrior = warrior_lookup.get(output_name)

        if output_name in elite_warriors:
            warrior.setdefault(tag,[]).append(label)
    
        if warrior is None:
            continue
        
        warrior["factions"] = faction_list
    
    return True

def customise_profiles(output, conf):
    """
    Apply customisations to heroes and warriors in the output.
    
    Customisations are applied in order: append, remove, update, rename.
    Rename is done last to ensure other operations reference the original name.
    """
    for level in ['heroes', 'warriors']:
        if 'customisations' not in conf or level not in conf['customisations']:
            continue
        
        customisations = conf['customisations'][level]
        
        # Build lookup for current level
        lookup = {
            obj["name"]: obj
            for obj in output["data"][level]
        }
        
        for custom in customisations:
            obj_name = custom.get("name")
            obj = lookup.get(obj_name)
            
            if obj is None:
                continue
            
            # Apply append - add items to list properties
            if 'append' in custom:
                for property_name, values in custom['append'].items():
                    if not isinstance(values, list):
                        continue
                    
                    # Create property if it doesn't exist
                    if property_name not in obj:
                        obj[property_name] = []
                    
                    # Ensure it's a list
                    if not isinstance(obj[property_name], list):
                        obj[property_name] = [obj[property_name]]
                    
                    # Append values (avoid duplicates)
                    for value in values:
                        if value not in obj[property_name]:
                            obj[property_name].append(value)
            
            # Apply remove - remove items from list properties
            if 'remove' in custom:
                for property_name, values in custom['remove'].items():

                    if property_name not in obj or not isinstance(values, list):
                        continue
                        
                    elif not isinstance(obj[property_name], list):
                        continue

                    # Remove matching values from the list
                    obj[property_name] = [
                        v for v in obj[property_name] 
                        if v not in values
                    ]
            
            # Apply update - set property values directly
            if 'update' in custom:
                for property_name, value in custom['update'].items():
                    obj[property_name] = value

            if "delete" in custom:
                for property_name in custom["delete"]:
                    del obj[property_name]
            
            # Apply rename last (after other operations reference the original name)
            if 'rename' in custom:
                new_name = custom['rename']
                obj['name'] = new_name
                # Update lookup with new name
                if obj_name in lookup:
                    del lookup[obj_name]
                lookup[new_name] = obj
    
    return True




def transplant_profiles(src, output, conf):
    """
        Transplants a profile from one section in the source, to another in the output
    """
    for profile in conf.get("customisations").get("transplant"):
        if "name" in profile and "fromSection" in profile and "toSection" in profile:
            profile_name = profile.get("name")
            from_section = profile.get("fromSection")
            to_section = profile.get("toSection")

            if from_section == "gear":
                _index = build_gear_index(src)
                output["data"].setdefault(to_section,[]).append(_index.get(profile_name))
                #case sensitive

            elif from_section == "heroes":
                _index = build_gear_index(src)
                output["data"].setdefault(to_section,[]).append(_index.get(profile_name))

            elif from_section == "warriors":
                _index = build_warrior_index(src)
                output["data"].setdefault(to_section,[]).append(_index.get(profile_name))

            else:
                raise Exception(f"Transplant is not configured to source from for {from_section}")
            
    return True

def build_custom_factions_file(source_file, config_file, output_file):
    conf = load_config(config_file)
    src = load_source(source_file)
    
    # Build set of all unique hero profiles to create BEFORE normalizing: (original_name, output_name) tuples
    hero_profiles_to_create = set()
    for faction in conf["customFactions"]:
        for hero_config in faction.get("heroes", []):
            if isinstance(hero_config, str):
                original_name = hero_config
                output_name = hero_config
            else:
                original_name = hero_config.get("name")
                output_name = hero_config.get("duplicateAs", original_name)
            
            hero_profiles_to_create.add((original_name, output_name))

    # Build set of all unique warrior profiles to create BEFORE normalizing: (original_name, output_name) tuples
    warrior_profiles_to_create = set()
    for faction in conf["customFactions"]:
        for warrior_config in faction.get("warriors", []):
            if isinstance(warrior_config, str):
                original_name = warrior_config
                output_name = warrior_config
            else:
                original_name = warrior_config.get("name")
                output_name = warrior_config.get("duplicateAs", original_name)
            
            warrior_profiles_to_create.add((original_name, output_name))
    
    # Build mapping of output_name -> [faction_names] for attaching factions
    hero_faction_mapping = {}  # output_name -> [(faction_name, heroic_tier), ...]
    warrior_faction_mapping = {}  # output_name -> [faction_name, ...]
    
    for faction in conf["customFactions"]:
        faction_name = faction["name"]
        
        for hero_config in faction.get("heroes", []):
            if isinstance(hero_config, str):
                output_name = hero_config
                heroic_tier = None
            else:
                output_name = hero_config.get("duplicateAs", hero_config.get("name"))
                heroic_tier = hero_config.get("heroicTier")
            
            if output_name not in hero_faction_mapping:
                hero_faction_mapping[output_name] = []
            hero_faction_mapping[output_name].append({
                "name": faction_name,
                "heroicTier": heroic_tier
            })
        
        for warrior_config in faction.get("warriors", []):
            if isinstance(warrior_config, str):
                output_name = warrior_config
            else:
                output_name = warrior_config.get("duplicateAs", warrior_config.get("name"))
            
            if output_name not in warrior_faction_mapping:
                warrior_faction_mapping[output_name] = []
            warrior_faction_mapping[output_name].append(faction_name)
    
    # Normalize faction configs to use only source names as strings
    normalize_faction_configs(conf)
    
    # Validate with normalized configs
    validate_custom_factions(src, conf)
    
    hero_index = build_hero_index(src)
    warrior_index = build_warrior_index(src)

    output = copy_skeleton(src)
    initialize_data(output, src, conf)

    add_heroes(output, hero_profiles_to_create, hero_index)
    add_warriors(output, warrior_profiles_to_create, warrior_index)
    attach_factions_with_mapping(output, conf, hero_faction_mapping, warrior_faction_mapping)
    transplant_profiles(src=src, output=output, conf=conf)
    customise_profiles(output=output, conf=conf)

    save_output(output, output_file)

if __name__ == "__main__":
    build_custom_factions_file(
        "mesbg.json",
        "new_factions_config.json",
        "lol27.json",
    )

    