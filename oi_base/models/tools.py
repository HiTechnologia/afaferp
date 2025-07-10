# -*- coding: utf-8 -*-
import re

def en_to_ar(value):
    if not isinstance(value, str):
        value = str(value)
    if not value:
        return value
    
    digits_map = {
        "0": "٠",
        "1": "١",
        "2": "٢",
        "3": "٣",
        "4": "٤",
        "5": "٥",
        "6": "٦",
        "7": "٧",
        "8": "٨",
        "9": "٩",
    }
    
    pattern = re.compile("|".join(digits_map.keys()))
        
    return pattern.sub(lambda x: digits_map[x.group()], value)
