"""Canonical QC tag definitions."""
from typing import Any
from copy import deepcopy
DEFAULT_LIGHT_TAGS = [{'name': '拖影', 'has_sub': True, 'subs': ['小范围', '大范围']}, {'name': '光变问题', 'has_sub': True, 'subs': ['＜30%', '＞30%']}, {'name': '反光白噪点', 'has_sub': False}, {'name': '反光多帧异常、不一致', 'has_sub': False}, {'name': '漏光', 'has_sub': False}, {'name': '其他', 'has_sub': False}]
DEFAULT_COMP_TAGS = [{'name': '物体穿模', 'has_sub': False}, {'name': '物体影子丢失', 'has_sub': False}, {'name': '物体被遮挡太多', 'has_sub': False}, {'name': '物体贴边框太近', 'has_sub': False}, {'name': '两个时间段内物体影子相似', 'has_sub': False}, {'name': '构图规避光变', 'has_sub': False}, {'name': '其他', 'has_sub': False}]

def get_default_light_tags() -> Any:
    return deepcopy(DEFAULT_LIGHT_TAGS)

def get_default_comp_tags() -> Any:
    return deepcopy(DEFAULT_COMP_TAGS)
