import collections
import os
import json
import orjson
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



def load_generic(path, filename:str, key:str|None='Id', load_db:bool=True, load_multipart:bool=False):
    #DB files take priority if they are present
    file_path = os.path.join(path, 'DB', filename)
    if not load_db or not os.path.exists(file_path): file_path = os.path.join(path, 'Excel', filename)

    return load_file(file_path, key, load_multipart)


def load_file(file, key:str|None='Id', load_multipart:bool=False):
    multipart_file = file.rsplit('.',1)[0]+ '$.' + file.rsplit('.',1)[1]

    if load_multipart and os.path.exists(multipart_file.replace('$', str(1))):
        #print(f"Found multipart version of {file}")
        data = []
        i = 1
        while os.path.exists(multipart_file.replace('$', str(i))):
            with open(multipart_file.replace('$', str(i)), encoding="utf8") as f: data += orjson.loads(f.read())['DataList']
            i += 1
        if key is not None: return {item[key]: item for item in data}
        else: return data
        
    elif os.path.exists(file): 
        with open(file, encoding="utf8") as f:
            data = orjson.loads(f.read())
        if key is not None: return {item[key]: item for item in data['DataList']}
        else: return data['DataList']
    
    else:
        print(f'WARNING - file {file} is not present')
        return {}


def load_file_grouped(path, filename, key='Id'):
    #DB files take priority if they are present
    file_path = os.path.join(path, 'DB', filename)
    if not os.path.exists(file_path): file_path = os.path.join(path, 'Excel', filename)
    with open(file_path, encoding="utf8") as f:
        data = orjson.loads(f.read())
    groups = collections.defaultdict(list)
    for item in data['DataList']:
        groups[item[key]].append(item)

    return dict(groups)



def load_costume_by_prefab(path):
    # TODO: find something better to use as the key
    data = load_file(os.path.join(path, 'Excel', 'CostumeExcelTable.json'), key='ModelPrefabName')
    # Only keep items where ProductionStep == 'Release'
    return {k: v for k, v in data.items() if v.get('ProductionStep') == 'Release'}



def load_data(path_primary, path_secondary, path_translation):
    return BlueArchiveData(
        campaign_stages=load_generic(path_primary, 'CampaignStageExcelTable.json'),
        campaign_stage_rewards=load_file_grouped(path_primary, 'CampaignStageRewardExcelTable.json', key='GroupId'),
        campaign_strategy_objects=load_generic(path_primary, 'CampaignStrategyObjectExcelTable.json'),
        campaign_units=load_generic(path_primary, 'CampaignUnitExcelTable.json'),
        characters= load_generic(path_primary, 'CharacterExcelTable.json'), #characters=load_characters(path_primary),
        costumes= load_generic(path_primary, 'CostumeExcelTable.json', key='CostumeGroupId'),
        costume_by_prefab = load_costume_by_prefab(path_primary),
        ground = load_generic(path_primary, 'GroundExcelTable.json'),
        currencies=load_generic(path_primary, 'CurrencyExcelTable.json', key='ID'),
        event_content_stages=load_generic(path_primary, 'EventContentStageExcelTable.json'),
        event_content_stage_rewards=load_generic(path_primary, 'EventContentStageExcelTable.json'),
        gacha_elements=load_file_grouped(path_primary, 'GachaElementExcelTable.json', key='GachaGroupID'),
        gacha_elements_recursive=load_file_grouped(path_primary, 'GachaElementRecursiveExcelTable.json', key='GachaGroupID'),
        gacha_groups=load_generic(path_primary, 'GachaGroupExcelTable.json', key='ID'),
        items=load_generic(path_primary, 'ItemExcelTable.json'),
        equipment=load_generic(path_primary, 'EquipmentExcelTable.json'),
        localization=load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeEtcExcelTable.json'),
        stages=None, #load_stages(path_primary),
    )


def load_regional_data(path):
    return BlueArchiveRegionalData(
        campaign_stage_rewards=load_file_grouped(path, 'CampaignStageRewardExcelTable.json', key='GroupId'),
    )


def load_strategies_translations(path):
    return load_file(os.path.join(path, 'Strategies.json'), key='Name')


def load_translations(path):
    return BlueArchiveTranslations(
        strategies=load_strategies_translations(path)
    )


def load_combined_localization(path_primary, path_secondary, path_translation, filename, key='Key'):

    data_primary = load_generic(path_primary, filename, key, load_db=True, load_multipart=True)
    data_secondary = load_generic(path_secondary, filename, key, load_db=True, load_multipart=True)
    data_aux = load_file(os.path.join(path_translation, filename), key, load_multipart=False)

    combined_keys = set(data_primary.keys()).union(data_secondary.keys())
    if data_aux:
        combined_keys = combined_keys.union(data_aux.keys())
        #print(f'Loading additional translations from {os.path.join(path_translation, filename)}')

    for index in combined_keys:
        if data_aux and index in data_aux:
            if index in data_primary and 'Jp' in data_primary[index] and data_aux[index]['Jp'] != data_primary[index]['Jp']:
                print(f"Warning - overwriting Jp text {index}:\n{data_primary[index]['Jp']}\n{data_aux[index]['Jp']}")
            data_primary[index] = data_aux[index]
        elif index in data_secondary:
            data_primary[index] = data_secondary[index]

    return data_primary


def load_stages(path_primary):
    data = {}
    
    for file in os.listdir(path_primary + '/Stage/'):
        if not file.endswith('.json'):
            continue
        
        with open(os.path.join(path_primary, 'Stage', file), encoding="utf8") as f:
            data[file[:file.index('.')]] = json.load(f)

    return data
