import collections
import re

from data import load_data, load_translations

Reward = collections.namedtuple('Reward', 'name,icon,tag,prob,amount')

ignore_item_id = [
    500100, #bundle of one of: Novice Activity Report / Lesser Enhancement Stone / Booster Ticket / (1 random T1 oopart). All story stages seem to have it 

]

def translate_group_name(text):
    text = re.sub('스테이지용', 'Stage', text)
    text = re.sub('스테이지', 'Stage', text)
    text = re.sub('장비', 'equipment', text)
    text = re.sub('티어', 'Tier', text)
    text = re.sub('박스', 'bundle', text)
    text = re.sub('묶음', 'recursive', text)
    text = re.sub('통합', 'integrated', text)
    text = re.sub('가챠', 'gacha', text)
    text = re.sub('크레딧', 'Credits', text)
    text = re.sub('공통', 'common', text)
    text = re.sub('오파츠', 'OOparts', text)
    text = re.sub('아이템', 'item', text)
    text = re.sub('그룹', 'group', text)
    text = re.sub('하급', 'low-class', text)
    text = re.sub('하드', 'hard', text)
    
    return text


def get_currency_rewards(reward, data):
    currency = data.currencies[reward['StageRewardId']]
    name_en = 'NameEn' in data.localization[currency['LocalizeEtcId']] and data.localization[currency['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, currency['Icon'], reward['RewardTag'], reward['StageRewardProb'] / 100, None)


def get_equipment_rewards(reward, data):
    item = data.equipment[reward['StageRewardId']]
    name_en = 'NameEn' in data.localization[item['LocalizeEtcId']] and data.localization[item['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, item['Icon'], reward['RewardTag'], reward['StageRewardProb'] / 100, None)


def get_item_rewards(reward, data):
    item = data.items[reward['StageRewardId']]
    name_en = 'NameEn' in data.localization[item['LocalizeEtcId']] and data.localization[item['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, item['Icon'], reward['RewardTag'], reward['StageRewardProb'] / 100, None)


def get_gacha_rewards(stage_reward, data):
    for reward in _get_gacha_rewards(stage_reward['StageRewardId'], stage_reward['StageRewardProb'] / 100, data):
        #print (reward)
        yield reward


def _get_gacha_rewards(group_id, stage_reward_prob, data):
    global ignore_item_id
    if group_id in ignore_item_id: 
        #print(f"Ignoring gacha group {group_id}")
        return

    gacha_group = data.gacha_groups[group_id]
    #print(f"Getting rewards for group_id {group_id}: {translate_group_name(gacha_group['NameKr'])}")
    if gacha_group['IsRecursive']:
        #print (f'This is a recursive group')
        yield from _get_gacha_rewards_recursive(group_id, stage_reward_prob, data)
        return

    for gacha_element in data.gacha_elements[group_id]:
        #print (gacha_element)
        type_ = gacha_element['ParcelType']
        if type_ == 'Currency':
            item = data.currencies[gacha_element['ParcelID']]
        elif type_ == 'Equipment':
            item = data.equipment[gacha_element['ParcelID']]
        elif type_ == 'Item':
            item = data.items[gacha_element['ParcelID']]

        name_en = 'NameEn' in data.localization[item['LocalizeEtcId']] and data.localization[item['LocalizeEtcId']]['NameEn'] or None
        #print (f'   {name_en}')
        prob = get_gacha_prob(gacha_element, data) * stage_reward_prob / 100
        amount = gacha_element['ParcelAmountMin'] == gacha_element['ParcelAmountMax'] and gacha_element['ParcelAmountMin'] or f"{gacha_element['ParcelAmountMin']}~{gacha_element['ParcelAmountMax']}"


        yield Reward(name_en, item['Icon'], 'Other', prob > 5 and round(prob,1) or round(prob,2), amount)


def _get_gacha_rewards_recursive(group_id, stage_reward_prob, data):
    for gacha_element in data.gacha_elements_recursive[group_id]:
        #print (f"Getting reward group {gacha_element['ParcelID']} for recursive element {gacha_element}")
        yield from _get_gacha_rewards(gacha_element['ParcelID'], stage_reward_prob, data)


def get_gacha_prob(gacha_element, data):
    #print (f"Current GachaGroupID is {gacha_element['GachaGroupID']}")
    #print (f"Current Prob is {gacha_element['Prob']}")
    total_prob = 0

    for element in data.gacha_elements[gacha_element['GachaGroupID']]:
        total_prob += element['Prob']
    #print (f"Total prob is {total_prob}")

    return gacha_element['Prob'] / total_prob * 100




def get_rewards(campaign_stage, data, regional_data = None):
    rewards = collections.defaultdict(list)
    for reward in _get_rewards(campaign_stage, data, regional_data):
        #print(reward)
        rewards[reward.tag].append(reward)

    return dict(rewards)


_REWARD_TYPES = {
    'Currency': get_currency_rewards,
    'Equipment': get_equipment_rewards,
    'Item': get_item_rewards,
    'GachaGroup': get_gacha_rewards
}


def _get_rewards(campaign_stage, data, regional_data):
    rewards = (regional_data is not None and campaign_stage['CampaignStageRewardId'] in regional_data.campaign_stage_rewards) and regional_data.campaign_stage_rewards[campaign_stage['CampaignStageRewardId']] or data.campaign_stage_rewards[campaign_stage['CampaignStageRewardId']]
    for reward in rewards:
        reward_type = reward['StageRewardParcelType']
        #print (reward_type)
        try:
            yield from _REWARD_TYPES[reward_type](reward, data)
        except KeyError:
            print(f'Unknown StageRewardParcelType: {reward_type}')
