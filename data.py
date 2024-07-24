import collections
import os
import json
#import pathlib

BlueArchiveData = collections.namedtuple(
    'BlueArchiveData',
    ['campaign_stages', 'campaign_stage_rewards', 'campaign_strategy_objects', 'campaign_units', 'characters', 'costumes', 'costume_by_prefab', 'ground',
     'currencies', 'equipment', 'event_content_stages', 'event_content_stage_rewards', 'gacha_elements', 'gacha_elements_recursive', 'gacha_groups',
     'items', 'localization', 'stages',
     ]
)
BlueArchiveTranslations = collections.namedtuple(
    'BlueArchiveTranslations',
    ['strategies']
)

BlueArchiveRegionalData = collections.namedtuple(
    'BlueArchiveRegionalData',
    ['campaign_stage_rewards'
     ]
)


def load_campaign_stages(path):
    return load_file(os.path.join(path, 'Excel', 'CampaignStageExcelTable.json'))


def load_campaign_stage_rewards(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'CampaignStageRewardExcelTable.json'), 'GroupId')


def load_campaign_strategy_objects(path):
    return load_file(os.path.join(path, 'Excel', 'CampaignStrategyObjectExcelTable.json'))


def load_campaign_units(path):
    return load_file(os.path.join(path, 'Excel', 'CampaignUnitExcelTable.json'))


# def load_characters(path):
#     # TODO: find something better to use as the key
#     return load_file(os.path.join(path, 'Excel', 'CharacterExcelTable.json'),
#                      key='ModelPrefabName',
#                      pred=lambda item: item['ProductionStep'] == 'Release')


def load_costume_by_prefab(path):
    # TODO: find something better to use as the key
    return load_file(os.path.join(path, 'Excel', 'CostumeExcelTable.json'),
                     key='ModelPrefabName',
                     pred=lambda item: item['ProductionStep'] == 'Release')


def load_currencies(path):
    return load_file(os.path.join(path, 'Excel', 'CurrencyExcelTable.json'), key='ID')


def load_data(path_primary, path_secondary, path_translation):
    return BlueArchiveData(
        campaign_stages=load_campaign_stages(path_primary),
        campaign_stage_rewards=load_campaign_stage_rewards(path_primary),
        campaign_strategy_objects=load_campaign_strategy_objects(path_primary),
        campaign_units=load_campaign_units(path_primary),
        characters= load_generic(path_primary, 'CharacterExcelTable.json'), #characters=load_characters(path_primary),
        costumes= load_generic(path_primary, 'CostumeExcelTable.json', key='CostumeGroupId'),
        costume_by_prefab = load_costume_by_prefab(path_primary),
        ground = load_generic(path_primary, 'GroundExcelTable.json'),
        currencies=load_currencies(path_primary),
        event_content_stages=load_event_content_stages(path_primary),
        event_content_stage_rewards=load_event_content_stage_rewards(path_primary),
        gacha_elements=load_gacha_elements(path_primary),
        gacha_elements_recursive=load_gacha_elements_recursive(path_primary),
        gacha_groups=load_gacha_groups(path_primary),
        items=load_items(path_primary),
        equipment=load_equipment(path_primary),
        localization=load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeEtcExcelTable.json'),
        stages=None, #load_stages(path_primary),
    )


def load_regional_data(path):
    return BlueArchiveRegionalData(
        campaign_stage_rewards=load_campaign_stage_rewards(path),
    )


#def load_data(path):
#    return _load_data(pathlib.Path(path))

def load_generic(path, filename, key='Id'):
    return load_file(os.path.join(path, 'Excel', filename), key)


def load_equipment(path):
    return load_file(os.path.join(path, 'Excel', 'EquipmentExcelTable.json'))


def load_event_content_stages(path):
    return load_file(os.path.join(path, 'Excel', 'EventContentStageExcelTable.json'))

def load_event_content_stage_rewards(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentStageRewardExcelTable.json'), 'GroupId')


def load_file(file, key='Id', pred=None):
    with open(file,encoding="utf8") as f:
        data = json.load(f)
    return {item[key]: item for item in data['DataList'] if not pred or pred(item)}


def load_file_grouped(file, key="Id"):
    with open(file,encoding="utf8") as f:
        data = json.load(f)
    groups = collections.defaultdict(list)
    for item in data['DataList']:
        groups[item[key]].append(item)

    return dict(groups)


def load_gacha_elements(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'GachaElementExcelTable.json'), 'GachaGroupID')


def load_gacha_elements_recursive(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'GachaElementRecursiveExcelTable.json'), 'GachaGroupID')


def load_gacha_groups(path):
    return load_file(os.path.join(path, 'Excel', 'GachaGroupExcelTable.json'), key='ID')


def load_items(path):
    return load_file(os.path.join(path, 'Excel', 'ItemExcelTable.json'))


def load_strategies_translations(path):
    return load_file(os.path.join(path, 'Strategies.json'), key='Name')


#def load_translations(path):
#    return _load_translations(pathlib.Path(path))


def load_translations(path):
    return BlueArchiveTranslations(
        strategies=load_strategies_translations(path)
    )


def load_combined_localization(path_primary, path_secondary, path_translation, filename, key='Key'):
    data_primary = load_file(os.path.join(path_primary, 'Excel', filename), key)
    data_secondary = load_file(os.path.join(path_secondary, 'Excel', filename), key)
    data_aux = None

    index_list = list(data_primary.keys())
    index_list.extend(x for x in list(data_secondary.keys()) if x not in index_list)

    if os.path.exists(os.path.join(path_translation, filename)):
        print(f'Loading additional translations from {path_translation}/{filename}')
        data_aux = load_file(os.path.join(path_translation, filename), key)

        index_list.extend(x for x in list(data_aux.keys()) if x not in index_list)

    for index in index_list:
        try: 
            if data_aux != None and index in data_aux:
                #print(f'Loading aux translation {index}')
                data_primary[index] = data_aux[index] 
            else :
                #print(f'Loading secondary data translation {index}')
                data_primary[index] = data_secondary[index] 
        except KeyError:
            #print (f'No secondary data for localize item {index}')
            continue
    
    return data_primary


def load_stages(path_primary):
    data = {}
    
    for file in os.listdir(path_primary + '/Stage/'):
        if not file.endswith('.json'):
            continue
        
        with open(os.path.join(path_primary, 'Stage', file), encoding="utf8") as f:
            data[file[:file.index('.')]] = json.load(f)

    return data
