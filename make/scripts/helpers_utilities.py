import csv
import json
import random

from pathlib import Path
from itertools import islice, count
from collections import defaultdict

class StatefulRandom:
    def __init__(self,seed):
        random.seed(seed)
        self._state = random.getstate()

    def shuffle(self,items):
        random.setstate(self._state)
        random.shuffle(items)
        self._state = random.getstate()

    def choice(self,items):
        random.setstate(self._state)
        item = random.choice(items)
        self._state = random.getstate()
        return item

# leaving this seed unchanged means
# that a huge diff won't be generated
# every time the output of these
# scripts is deployed. This state 
# needs to be global in order for 
# participants to experience the
# order of answers as random.
rng = defaultdict(lambda: StatefulRandom(1))

def write_output(dir_out, structure):
    for path, content in structure.items():
        path = Path(f"{dir_out}/{path}")

        if path.suffix == ".json" and isinstance(content,dict):
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=4, ensure_ascii=False)
            continue

        if path.suffix != ".json" and isinstance(content,list):
            path.mkdir(parents=True, exist_ok=True)
            for i,page in enumerate(content,1):
                with open(f"{path}/{i}.json", 'w', encoding='utf-8') as f:
                    json.dump(page, f, indent=4, ensure_ascii=False)
            continue

        raise Exception()

def get_groupnames():
    yield 'treatment'
    yield 'control'

def dir_safe(text):
    return text.replace("/","%2F").replace("\\","%5C").replace("+","%2B")

def is_int(val):
    try:
        int(val)
    except ValueError:
        return False
    else:
        return True

def is_yesno(values):
    return set([v.lower() for v in values]) == set(["yes","no"])

def has_value(value):
    return value and value.strip() and value.upper() not in ["NA","N/A","N\\A"]

def clean_up_unicode(text):
    if not text: return ""
    return text.replace("\u00e2\u20ac\u2122", "'").replace("\u2026", "...").replace("\u2013", " - ") \
        .replace("\u2014", " - ").replace("\u201c", '"').replace("\u201d", '"').replace("\\n", "\n") \
        .replace("\u2019", "'").replace("\u00e1", "á").replace("\u00e9", "é").replace("\u00ed", "í") \
        .replace("\u00f3", "ó").replace("\u00fa", "ú").replace(u'\xf1', 'n').replace("\u00fc", "ü") \
        .replace("\u00c1", "Á").replace("\u00c9", "É").replace("\u00cd", "Í").replace("\u00d3", "Ó") \
        .replace("\u00da", "Ú").replace("\u00d1", "Ñ").replace("\u00dc", "Ü").replace("  ", " ").strip()

def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def get_motivations(file_path):
    motivation_lst = []
    motivation_num = 0
    with open(file_path, "r") as read_obj:
        reader = csv.reader(read_obj)
        next(reader)
        for row in reader:
            motivation = row[1]
            if motivation not in (None, ""):
                motivation_num += 1
                motivation_lst.append([f"Motivational Statement #{motivation_num}", motivation])

    return motivation_lst

def get_strategies(file_path):
    """A function that reads in the file of emotion regulation tips and outputs a dictionary with the ER tips for
    each domain

        :param file_path: string path to ER tips file (.csv)
        :return: dictionary {"Domain" : [index, [ [resource, text], [resource, text]...] ] }
            * keys (str) = domains
            * fields (list) = [index, domain_list_of_ER_tips]
            * domain_list_of_ER_tips (list of lists) = [[Estrategia de Regulación Emocional # 1, text_1], [Estrategia de Regulación Emocional# 2, text_2]]
                * each list WITHIN the list is [Estrategia de Regulación Emocional # 1, text]

        File I used to make this: https://docs.google.com/spreadsheets/d/1kenROWNI498AcMhjElrFQD9IjOmnVGInVB8BShSYSx8/edit#gid=0
        """
    strats = defaultdict(list)
    with open(file_path, 'r', encoding='utf-8') as f:

        rows = iter(csv.reader(f))

        first_row = next(rows)
        domains = list(filter(None,[r.strip() for r in first_row[1:]]))

        for i,row in enumerate(rows,1):
            for j,domain in enumerate(domains,1):
                if row[j]: strats[domain].append([f"Emotion Regulation Strategy #{i}", row[j]])

    return strats

def get_tips(file_path):
    """ Function that reads in the tips file and outputs a list of the tips

    :param file_path:
    :return: list of lists,[ [Tip #1, text], [Tip #2, text]...]

    https://docs.google.com/spreadsheets/d/1kenROWNI498AcMhjElrFQD9IjOmnVGInVB8BShSYSx8/edit#gid=2086298502
    """

    tips = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i,row in enumerate([r for r in islice(csv.reader(f),1,None) if r[1]]):
            if row[1].strip():
                tips.append([f"Tip #{i}", row[1]])
    return tips

def get_resources(file_path):
    """ Function that reads in the tips file and outputs a list of the tips

    :param file_path:
    :return: list of lists,[ [Tip #1, text], [Tip #2, text]...]

    https://docs.google.com/spreadsheets/d/1kenROWNI498AcMhjElrFQD9IjOmnVGInVB8BShSYSx8/edit#gid=2086298502
    """

    resources = defaultdict(list)
    with open(file_path, 'r', encoding='utf-8') as f:
        rows = iter(csv.reader(f))

        first_row = next(rows)
        domains = list(filter(None,[r.strip() for r in first_row[1:]]))
        
        for row in islice(rows,1,None):
            for i,domain in enumerate(domains):
                domain_index = 1 + i*3
                if row[domain_index].strip():
                    resources[domain].append(row[domain_index:domain_index+3])

    return resources

def create_puzzle(scenario):

    if not has_value(scenario): return None, None
    punctuation_marks = "?.!"

    puzzle_text = scenario
    last_word   = scenario.split()[-1].strip().strip(punctuation_marks)
    puzzle_word = last_word

    puzzle_text = rreplace(puzzle_text, f" {puzzle_word}", "..", 1)

    return puzzle_text, puzzle_word

def shuffle(items,key=None):
    rng[key].shuffle(items)

def choice(items,key=None):
    return rng[key].choice(items)

def lower(str):
    return str.lower() if str else ""

def upper(str):
    return str.upper() if str else ""

def media_url(media):
    if media and media.strip():
        media = lower(media).strip()
        assert Path(f"./src/images/{media}").exists()
        return f"./images/{media}"
    return ""

def get_page_index(scenario, session, position):
    curr_num  = None
    scn_index = 0
    neg_index = 0

    scenario = lower(scenario).strip()

    for i, page in enumerate(session):
        if curr_num != page["scenario_num"]:
            curr_num = page["scenario_num"]
            scn_index += 1
            neg_index += int(page.get("type") == "negative")

            if position == "before":
                if scenario == "first negative" and neg_index == 1:
                    return i
                if scenario != "first negative" and scn_index == int(scenario[8:]):
                    return i

            if position == "after":
                if scenario == "first negative" and neg_index == 1 and page.get("type") != "negative":
                    return i-1
                if scenario != "first negative" and scn_index == int(scenario[8:])+1:
                    return i-1

    if position == "after" and scenario != "first negative" and scn_index == int(scenario[8:]):
        return i

    return None

def get_reminder_element(reminder,position,count):
    if not reminder: return None
    is_image = ".png" in reminder or ".jpg" in reminder or ".jpeg" in reminder
    element = {"type":"text", "text": reminder} if not is_image else {"type":"media", "url": media_url(reminder)}
    return { "elements": [ element ], "position": position, "information_count": count }
