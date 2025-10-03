from overlay import BonusInfo, EnemyInfo, Marker
from tilemap import BrokenTile, HideTile, HideTriggerTile, NormalTile, PortalEntranceTile, PortalExitTile, PortalTile, \
    SpawnTile, SpawnTriggerTile, StartTile, SwitchDownTile, SwitchUpTile, ToggleDownTile, ToggleUpTile


def get_strategies(map, data):
    #get actual spawn events list to check against, some entities may be placed on the map but not actually spawned
    spawned_entity_ids = []
    for event in map['Events']:
        for command in event['HexaCommands']:
            if 'HexaCommandStrategySpawn' in command['$type']:
                for spawn in command['StrategyEntityIds']:
                    spawned_entity_ids.append(spawn)
    spawned_entity_ids = set(spawned_entity_ids)

    for hexa_strategy in map['hexaStrageyList']:
        if hexa_strategy['EntityId'] not in spawned_entity_ids:
            print(f"Skipping entity {hexa_strategy['EntityId']} at {location} because it is never spawned")
            continue
        location = (hexa_strategy['Location']['x'], hexa_strategy['Location']['y'], hexa_strategy['Location']['z'])
        yield location, data.campaign_strategy_objects[hexa_strategy['Id']]


def get_bonus_infos(strategies):
    for location, strategy in strategies:
        prefab_name = strategy['PrefabName']
        if prefab_name in [
            'SightObject_On_01_Mesh',
            'HealObject_01_Mesh',
            'BuffAttackObject_01_Mesh',
            'BuffDefenseObject_01_Mesh',
            'RewardObject_OneTime_01_Mesh'
        ]:
            yield location, BonusInfo(prefab_name)


def get_enemy_infos(map, data):
    for unit in map['hexaUnitList']:
        campaign_unit = data.campaign_units[unit['Id']]

        # ground = data.ground[campaign_unit['Id']]
        # print(f"StageFileName {ground['StageFileName']}")
        # stagefile = data.stages[ground['StageFileName'][0].lower()]

        # for template in json_find_key(stagefile, 'SpawnTemplateId'):
        #     print(template)
            # if template != '' and template in devname_characters and template not in spawn_templates:
            #     spawn_templates[template] = devname_characters[template]     

        #NOTE TO SELF
        #going through spawn templates in actual stage file seems to be the proper way to get ACTUAL character info
        #currently data is linked in a way that can break because PrefabName is shared across several versions of the unit

        costume = data.costume_by_prefab[campaign_unit['PrefabName']]
        character = data.characters[costume['CostumeGroupId']]

        location = unit['Location']['x'], unit['Location']['y'], unit['Location']['z']
        yield location, EnemyInfo(
            campaign_unit['AIMoveType'],
            campaign_unit['Grade'],
            character['BulletType'],
            character['ArmorType'],
            campaign_unit['Grade'] == 'Boss'
        )


def get_start_tiles(strategies):
    for location, strategy in strategies:
        if strategy['StrategyObjectType'] in ['Start', 'FixedStart01', 'FixedStart02', 'FixedStart03', 'FixedStart04']:
            yield location


def get_one_way_portals(strategies):
    entrances, exits = {}, {}
    for location, strategy in strategies:
        if strategy['StrategyObjectType'] == 'PortalOneWayEnterance':
            try:
                yield location, exits[strategy['PortalId']]
            except KeyError:
                pass

            entrances[strategy['PortalId']] = location
        elif strategy['StrategyObjectType'] == 'PortalOneWayExit':
            try:
                yield entrances[strategy['PortalId']], location
            except KeyError:
                pass

            exits[strategy['PortalId']] = location


def get_two_way_portals(strategies):
    portals = {}
    for location, strategy in strategies:
        if strategy['StrategyObjectType'] == 'Portal':
            try:
                yield location, portals[strategy['PortalId']]
            except KeyError:
                portals[strategy['PortalId']] = location


def get_toggles(strategies, toggle_prefab_names = ['SingleSwitchObject_01_UP', 'SingleSwitchObject_02_UP', 'SingleSwitchObject_03_UP', 'SingleSwitchObject_01_Down', 'SingleSwitchObject_02_Down', 'SingleSwitchObject_03_Down']):
    for location, strategy in strategies:
        if strategy['StrategyObjectType'] == 'SwitchToggle' and strategy['PrefabName'] in toggle_prefab_names:
            try:
                yield location, strategy['PrefabName'].rsplit('_')[-1], strategy['SwithId']
            except KeyError:
                pass


def _get_switches(strategies, switch_object_type, switch_id):
    for location, strategy in strategies:
        if strategy['StrategyObjectType'] == switch_object_type and strategy['SwithId'] == switch_id:
            try:
                yield location
            except KeyError:
                pass


def get_down_switches(strategies, switch_id):
    return _get_switches(
        strategies,
        'SwitchMovableWhenToggleOff',
        switch_id
    )


def get_up_switches(strategies, switch_id):
    return _get_switches(
        strategies,
        'SwitchMovableWhenToggleOn',
        switch_id
    )


def get_command_with_type(event, type_):
    try:
        return next(command for command in event['HexaCommands'] if type_ in command['$type'])
    except StopIteration:
        raise KeyError


def get_condition_with_type(event, type_):
    try:
        return next(condition for condition in event['HexaConditions'] if type_ in condition['$type'])
    except StopIteration:
        raise KeyError


def get_hide_tiles(map):
    for event in map['Events']:
        try:
            condition = get_condition_with_type(event, 'HexaConditionArriveTile')
            command = get_command_with_type(event, 'HexaCommandTileHide')
        except KeyError:
            continue

        trigger = (condition['TileLocation']['x'], condition['TileLocation']['y'], condition['TileLocation']['z'])
        for hide in command['TileLocations']:
            yield trigger, (hide['x'], hide['y'], hide['z'])


def get_spawn_tiles(map):
    for event in map['Events']:
        try:
            condition = get_condition_with_type(event, 'HexaConditionArriveTile')
            command = get_command_with_type(event, 'HexaCommandTileSpawn')
        except KeyError:
            continue

        trigger = (condition['TileLocation']['x'], condition['TileLocation']['y'], condition['TileLocation']['z'])
        for spawn in command['TileLocations']:
            yield trigger, (spawn['x'], spawn['y'], spawn['z'])


def get_tiles(map, data):
    strategies = list(get_strategies(map, data))
    bonus_infos = dict(get_bonus_infos(strategies))
    enemy_infos = dict(get_enemy_infos(map, data))
    for tile in map['hexaTileList']:
        location = (tile['Location']['x'], tile['Location']['y'], tile['Location']['z'])
        yield location, NormalTile(overlay=[bonus_infos.get(location) or enemy_infos.get(location)])

    for location in get_start_tiles(strategies):
        yield location, StartTile()

    number = 0
    for entrance, exit in get_one_way_portals(strategies):
        number += 1
        yield entrance, PortalEntranceTile(overlay=[Marker(number)])
        yield exit, PortalExitTile(overlay=[Marker(number)])

    for entrance, exit in get_two_way_portals(strategies):
        number += 1
        yield entrance, PortalTile(overlay=[Marker(number)])
        yield exit, PortalTile(overlay=[Marker(number)])

    for trigger, hide in get_hide_tiles(map):
        if trigger == hide:
            # It's a broken tile
            yield trigger, BrokenTile(overlay=[bonus_infos.get(trigger) or enemy_infos.get(trigger)])
        else:
            number += 1
            yield trigger, HideTriggerTile(overlay=[Marker(number)])
            yield hide, HideTile(overlay=[Marker(number), bonus_infos.get(hide) or enemy_infos.get(hide)])

    for trigger, spawn in get_spawn_tiles(map):
        number += 1
        yield trigger, SpawnTriggerTile(overlay=[Marker(number)])
        yield spawn, SpawnTile(overlay=[Marker(number)])

    for toggle_location, toggle_type, switch_id in get_toggles(strategies):
        number += 1

        match toggle_type:
            case 'UP':
                yield toggle_location, ToggleUpTile(overlay=[Marker(number), bonus_infos.get(toggle_location) or enemy_infos.get(toggle_location)])
            case 'Down':
                yield toggle_location, ToggleDownTile(overlay=[Marker(number), bonus_infos.get(toggle_location) or enemy_infos.get(toggle_location)])
       
        for switch in get_down_switches(strategies, switch_id):
            yield switch, SwitchDownTile(overlay=[Marker(number), bonus_infos.get(switch) or enemy_infos.get(switch)])    
        for switch in get_up_switches(strategies, switch_id):
            yield switch, SwitchUpTile(overlay=[Marker(number), bonus_infos.get(switch) or enemy_infos.get(switch)])    


# def json_find_key(json_input, lookup_key):
#     if isinstance(json_input, dict):
#         for k, v in json_input.items():
#             if k == lookup_key:
#                 yield v
#             else:
#                 yield from json_find_key(v, lookup_key)
#     elif isinstance(json_input, list):
#         for item in json_input:
#             yield from json_find_key(item, lookup_key)
