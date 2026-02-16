import csv
import shutil

from collections import defaultdict
from itertools import islice, cycle, chain
from pathlib import Path

from helpers_pages import create_scenario_pages, create_survey_page,create_resource_page
from helpers_pages import create_long_pages, create_write_your_own_page, create_video_page
from helpers_utilities import get_strategies, get_tips, clean_up_unicode, has_value, create_puzzle
from helpers_utilities import dir_safe, shuffle, write_output, media_url, lower, get_page_index 
from helpers_utilities import get_reminder_element, get_resources

dir_root = "./make"
dir_csv    = f"{dir_root}/CSV"
dir_out    = f"{dir_root}/~out"

Path(dir_out).mkdir(parents=True,exist_ok=True)

def flat(dictionary, key):
    return list(chain.from_iterable(dictionary[lower(key)].values()))

def _create_practice_pages():
    with open(f"{dir_csv}/dose1_scenarios - HTC.csv", "r", encoding="utf-8") as dose1_read_obj:  # scenarios for first dose in file
        
        scenario_num = 0
        for row in islice(csv.reader(dose1_read_obj),1,None):

            # First, add the video that goes before each scenario
            yield create_video_page(scenario_num+1)

            domain, label = row[0].strip(), row[3]
            puzzle1,puzzle2 = map(create_puzzle,row[i:i+2])
            question, choices, answer = row[i+2], row[7:9], row[7]
            image_url = media_url(row[10])

            choices = [c.strip() for c in choices]
            answer = answer.strip()

            shuffle(choices)

            yield from create_scenario_pages(domain=domain, title=label, scenario_num=scenario_num,
                                                    puzzle_text_1=puzzle1[0], word_1=puzzle1[1],
                                                    comp_question=question, answers=choices,
                                                    correct_answer=answer, word_2=puzzle2[1],
                                                    puzzle_text_2=puzzle2[0], image_url=image_url,
                                                    is_first=scenario_num==0)
            scenario_num += 1

def _create_survey_page(row):
    text = clean_up_unicode(row[4])

    title = row[1].strip()
    input_1 = row[5]
    minimum = row[7]
    maximum = row[8]
    media = media_url(row[9])
    items = row[10]
    image_framed = row[11]
    timeout = row[12]
    show_buttons = row[13]
    variable_name = row[16]
    conditions = row[17]
    input_name = row[18]

    is_html = row[0] == "MDS-UPDRS"

    return create_survey_page(condition=conditions, text=text,
                              show_buttons=show_buttons, media=media,
                              image_framed=image_framed, values=items,
                              input=input_1,variable_name=variable_name, 
                              title=title, output_name=input_name, minimum=minimum,
                              maximum=maximum, timeout=timeout,is_html=is_html)

def domain_selection_text():
    return (
        "The domains listed here are some areas that may cause you to feel anxious. " 
        "Please select the one that you'd like to work on during today's training."
        "\n\nWe encourage you to choose different domains to practice thinking "
        "flexibly across areas of your life!"
    )

def create_long_sessions():
    sessions = defaultdict(list)

    with open(f"{dir_csv}/LEIA Interventions, Resources, and Tips - Long Scenarios.csv", "r",encoding="utf-8") as read_file:
        for row in islice(csv.reader(read_file),2,None):

            if not row: continue # Skip empty lines

            domain_1 = row[0].strip()
            domain_2 = row[1].strip() if row[1] else None
            label = row[3]
            image_url = media_url(row[6])
            scenario_description = row[4]
            thoughts = row[7:12]
            feelings = row[12:17]
            behaviors = row[17:22]
            
            if not has_value(scenario_description) or not has_value(label): continue

            dose = create_long_pages(label=label, scenario_description=scenario_description,
                                    thoughts=thoughts, feelings=feelings, behaviors=behaviors, 
                                    image_url=image_url)

            if domain_1: sessions[domain_1].append(dose)
            if domain_2: sessions[domain_2].append(dose)
    
    # shuffle each list of long scenario page groups
    for domain in sessions: shuffle(sessions[domain])

    return {k:iter(cycle(v)) for k,v in sessions.items()}

def create_short_sessions():
    d_sessions  = defaultdict(list)
    d_scenarios = defaultdict(list)

    with open(f"{dir_csv}/LEIA Interventions, Resources, and Tips - Short Scenarios.csv","r", encoding="utf-8", newline='') as read_obj:

        for row in islice(csv.reader(read_obj),1,None):

            domain = row[0].strip()
            title  = row[3]

            if not domain or not title: continue

            scenarios = d_scenarios[domain]
            sessions  = d_sessions[domain]

            # we don't have wyo

            tipe = "unknown" #positive or negative

            image_url = media_url(row[10])
            puzzle1,puzzle2 = map(create_puzzle,row[4:6])

            if puzzle1 == (None,None): continue

            comp_question, choices, answer  = row[6], row[7:9], row[7]

            choices = [c.strip() for c in choices]
            answer = answer.strip()

            if lower(choices[0]).strip() in ['yes','no']: choices = ["Yes","No"]

            shuffle(choices)

            if row[11]: letters_missing = row[11]

            is_first_scenario = len(scenarios) == 0

            scenarios.append(
                create_scenario_pages(domain=domain, title=title, 
                                        scenario_num=len(d_scenarios[domain]),
                                        puzzle_text_1=puzzle1[0], word_1=puzzle1[1],
                                        comp_question=comp_question, answers=choices,
                                        correct_answer=answer, word_2=puzzle2[1],
                                        puzzle_text_2=puzzle2[0], image_url=image_url,
                                        n_missing=letters_missing,
                                        is_first=is_first_scenario, tipe=tipe
                )
            )

            if len(scenarios) == 10:
                sessions.append(list(chain(*scenarios)))
                scenarios.clear()

    return d_sessions

def create_surveys():
    accepted = [f"beforedomain_all", f"afterdomain_all"]
    accepted = [lower(a) for a in accepted]
    surveys  = defaultdict(lambda:defaultdict(list))
    notin = set()

    # Open the file with all the content
    with open(f"{dir_csv}/MTM_survey_questions - Final_{popname} MTM_survey_questions.csv", "r", encoding="utf-8") as read_obj:
        for row in islice(csv.reader(read_obj),1,None):
            lookup_id, subgroup_id = f"{row[3]}_{row[2]}".lower(), row[0]

            if lookup_id not in accepted:
                notin.add(lookup_id)
            elif row[2]:
                surveys[lookup_id][subgroup_id].append(_create_survey_page(row))

    return surveys

def create_write_your_own_session():
    pages = []
    with open(f"{dir_csv}/MTM_write_your_own.csv", "r", encoding="utf-8") as f:
        for row in islice(csv.reader(f),1,None):
            text = clean_up_unicode(row[4])
            if text:
                title = row[1]
                input_1 = row[5]
                input_name = row[18]
                pages.append(create_write_your_own_page(text, input_1, title, input_name))
    return pages

def create_resource_dose_creator():
    strategies  = get_strategies(file_path=f"{dir_csv}/LEIA Interventions, Resources, and Tips - Strategies.csv")
    tips        = get_tips(file_path=f"{dir_csv}/LEIA Interventions, Resources, and Tips - Tips.csv")
    resources   = get_resources(file_path=f"{dir_csv}/LEIA Interventions, Resources, and Tips - Resources.csv")

    return lambda domain: [create_resource_page(tips, strategies, resources, domain)]

surveys         = create_surveys()
short_sessions  = create_short_sessions()         # dict of short session iter by domain
long_sessions   = create_long_sessions()          # dict of long session cycle by domain
resources       = create_resource_dose_creator()  # lambda that takes a domain and returns a dose

domains  = short_sessions.keys()
sessions = defaultdict(list)

for domain in domains:
    for short_session in short_sessions[domain]:
        if sessions[domain] and len(sessions[domain]) % 5 == 0:
            sessions[domain].append(next(long_sessions[domain]) + resources(domain))
        else:
            sessions[domain].append(short_session + resources(domain))

# Define folders
folders = {}
folders['sessions/__flow__.json'] = {"mode":"select", "title_case": True, "column_count":2, "text": domain_selection_text(), "title":"MindTrails" }
folders['sessions/__before__'] = flat(surveys,"beforedomain_all")
folders['sessions/__after__'] = flat(surveys,"afterdomain_all")

for domain, doses in sessions.items():
    folders[f'sessions/{dir_safe(domain)}/__flow__.json'] ={"mode":"sequential", "take":1, "repeat":True}
    for i, dose in enumerate(doses,1):
        folders[f'sessions/{dir_safe(domain)}/{i}'] = dose

# Delete old JSON
shutil.rmtree(f"{dir_out}/sessions",ignore_errors=True)

# Write new JSON
write_output(f"{dir_out}", folders)
