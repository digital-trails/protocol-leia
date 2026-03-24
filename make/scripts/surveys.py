import csv
import shutil

from collections import defaultdict
from itertools import islice, chain
from pathlib import Path

from helpers_pages import create_scenario_pages, create_survey_page,create_video_page
from helpers_utilities import clean_up_unicode, create_puzzle, shuffle, write_output, media_url, lower

dir_root = "./make"
dir_csv  = f"{dir_root}/CSV"
dir_out  = f"{dir_root}/~out"

Path(dir_out).mkdir(parents=True,exist_ok=True)

def flat(dictionary):
    return list(chain.from_iterable(dictionary.values()))

def _create_survey_page(row):
    
    text = clean_up_unicode(row[2])
    title = row[1].strip()

    input_type    = row[3]
    values        = row[4]
    variable_name = row[5]
    condition     = row[6]
    output_name   = row[7]
    media         = media_url(row[8])
    image_framed  = "true"
    show_buttons  = None
    is_html       = None
    timeout       = None

    return create_survey_page(condition=condition, text=text, show_buttons=show_buttons, 
                              media=media, image_framed=image_framed, values=values, 
                              input_type=input_type, variable_name=variable_name, title=title, 
                              output_name=output_name, timeout=timeout, is_html=is_html)

def _create_practice_pages():
    with open(f"{dir_csv}/dose1_scenarios - HTC.csv", "r", encoding="utf-8") as dose1_read_obj:  # scenarios for first dose in file
        
        scenario_num = 0
        for row in islice(csv.reader(dose1_read_obj),1,None):

            # First, add the video that goes before each scenario
            yield create_video_page(scenario_num+1)

            domain, label = row[0].strip(), row[3]
            puzzle1,puzzle2 = map(create_puzzle,row[4:6])
            question, choices, answer = row[6], row[7:9], row[7]
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

survey_pages = defaultdict(lambda: defaultdict(list))

#Read the survey questions
with open(f"{dir_csv}/LEIA Interventions, Resources, and Tips - Surveys.csv", "r", encoding="utf-8") as read_obj:

    for row in islice(csv.reader(read_obj),1,None):

        survey = lower(row[0])
        section = row[1]

        if survey in ["intro","eod"]: 

            if section != "Practice CBM-I":
                survey_pages[survey][section].append(_create_survey_page(row))
            else:
                survey_pages[survey][section].extend(_create_practice_pages())

# Define folders
folders = {
    'intro': flat(survey_pages["intro"]),
    'end of day': flat(survey_pages["eod"])
}

# Delete old JSON
for key in folders.keys(): 
    shutil.rmtree(f"{dir_out}/{str.join('/',key.split('/')[:3])}",ignore_errors=True)

# Write new JSON
write_output(dir_out, folders)