"""pixelkit.characters.cast_sleep - 《熬夜副本》人物造型（v0.13，human.Look 预设；均为 Q 版风格化，不是肖像）。"""
from .human import Look

KLEITMAN = Look(hair='side', hair_col='#2a2226', skin='#eec29a', glasses='round', glasses_col='#3a2a1a', stubble=False,
                bags=False, cloth='cardigan', cloth_col='#7a5a3e', accent='#a83a2a', seed=1)          # 1938 生理学家
STUDENT = Look(hair='short', hair_col='#5a3a26', skin='#f2c8a0', cloth='shirt_tie', cloth_col='#d8d2c0', accent='#3a5a8a', seed=2)
ASERINSKY = Look(hair='messy', hair_col='#1e1a20', skin='#efc49c', glasses='square', glasses_col='#222222', cloth='shirt_tie',
                 cloth_col='#c8c0b0', accent='#6a3a2a', bags=True, seed=3)                             # 1953 穷研究生
KID = Look(hair='short', hair_col='#6a4428', skin='#f6cfa8', cloth='tshirt', cloth_col='#7aa0d8', seed=4)
GARDNER = Look(hair='short', hair_col='#8a5a30', skin='#f2c8a0', cloth='tshirt', cloth_col='#e8e4d8', accent='#c8302a', seed=5)  # 1964 高中生
SUBJECT = Look(hair='side', hair_col='#2a2228', skin='#eec29a', cloth='hoodie', cloth_col='#6a7a90', bags=True, seed=6)          # 2003 受试者
KONOPKA = Look(hair='side', hair_col='#3a2a22', skin='#efc49c', glasses='square', glasses_col='#2a2a30', stubble=True,
               cloth='shirt_tie', cloth_col='#e8e2d4', accent='#5a6a3a', seed=7)                     # 1971 研究生
LAUREATES = [Look(hair='bald', skin='#f0c8a4', glasses='round', cloth='suit', cloth_col='#2a2a34', accent='#e8e8e8', seed=11),
             Look(hair='short', hair_col='#d8d8dc', skin='#f2cca8', cloth='suit', cloth_col='#2a2a34', accent='#e8e8e8', seed=12),
             Look(hair='side', hair_col='#b8b0a8', skin='#eec4a0', glasses='square', cloth='suit', cloth_col='#2a2a34', accent='#e8e8e8', seed=13)]
