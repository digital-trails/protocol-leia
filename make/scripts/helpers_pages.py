import csv
import json

from typing import Literal
from itertools import islice
from typing import Tuple, Iterable

from helpers_utilities import clean_up_unicode, has_value, is_yesno, is_int, shuffle, choice, lower

dir_root = "./make"
dir_csv  = f"{dir_root}/CSV"

def parse_value(value: str):
    value = value.strip()
    i = value.index(".") if "." in value else 0
    k = value[:i] if value[:i].isdigit() else None
    v = value[i+1:].strip()
    return (k, v)

def parse_values(values: str):
    if not values: return []
    return list(map(parse_value,clean_up_unicode(values).split(";")))

def to_button_value(item: Tuple[str,str]):
    p = item[1][0] if item[1][0] in ["^","!"] else ""
    k = str(item[0]) if item[0] is not None else None
    v = item[1][1:] if item[1][0] in ["^","!"] else item[1]
    return f"{p}{k}::{v}" if k else f"{p}{v}"

def to_button_values(items: Iterable[Tuple[int,str]]):
    return list(map(to_button_value,items))

def create_conditions(args):

    if not args: return {}

    tokens = [a.strip() for a in args.split(" ") if a.strip()]
    tokens.reverse()
    conjunctions = ["&","|"]

    condition = []
    while tokens:
        token = tokens.pop()

        if token == "in":
            items = []
            condition.append(token)
            condition.append(items)
            while tokens:
                token = tokens.pop()
                if token in conjunctions:
                    tokens.append(token)
                    break
                items.append(int(token) if token.isdigit() else token)
        elif token.isdigit():
            condition.append(int(token))
        elif token == "&":
            condition.append("&&")
        elif token == "|":
            condition.append("||")
        else:
            condition.append(token)

    return { "condition": condition }

def create_nav_conditions(show_next:Literal["WhenCorrect","AfterTimeout","Never","WhenComplete"]=None,timeout=None,inputs=None):
    show_next = lower(show_next)
    inputs = inputs or []
    if 'puzzle' in list(map(lower,inputs)):
        return {"navigation_conditions": "wait_for_correct"}
    if timeout:
        return {"navigation_conditions": [{"wait_for_time": int(timeout)*1000}, "wait_for_click"]}
    # if timeout:
    #     return {"navigation_conditions": [{"wait_for_time": int(timeout)}]}
    if show_next == "whencorrect":
        return {"navigation_conditions": ["wait_for_correct", "wait_for_click"]}
    if show_next == "whencomplete":
        return {"navigation_conditions": ["wait_for_complete", "wait_for_click"]}
    return {}

def create_input(tipe, values, output_name, variable_name = ""):
    if not tipe: return

    assert output_name, "all inputs require a name"

    tipe = lower(tipe)

    shared = {}
    if output_name: shared["name"] = output_name
    if variable_name: shared["variable_name"] = variable_name

    if tipe == "entry":
        yield {"type": "Entry", **shared}
        return

    if tipe == "slider":
        values = parse_values(values)
        others = to_button_values(values[3:])
        _min, _max = int(values[0][0]), int(values[1][0])
        yield {"type": "Text", "Text": f"{values[0][1]}\n\n{values[1][1]}"}
        yield {"type": "Slider", "min": _min, "max": _max, "others": others, **shared}
        return

    if tipe == "single":
        values = to_button_values(parse_values(values))
        yield {"type": "Buttons", "buttons": values, "ColumnCount": (2 if is_yesno(values) else 1), **shared}
        return

    if tipe == "multi":
        values = to_button_values(parse_values(values))
        yield {"type": "Buttons", "buttons": values, "multiselect": True, **shared}
        return

    if tipe == "scheduler": 
        yield {"type": "Scheduler", "days_ahead": int(values), "action": "flow://flows/session", "count":1, "message": "It's time for your session."}
        return

    if tipe == "timedtext": 
        yield {"type": "TimedText", "texts": values, "Duration": 15000}
        return

    if tipe == "puzzle":
        yield {
            "type": "WordPuzzle",
            "correct_feedback": "Correct",
            "incorrect_feedback": "Whoops! That doesn't look right. Please wait a moment and try again.",
            "incorrect_delay": 5000,
            "display_delay": 2000,
            "words": values,
            **shared }
        return

def create_long_pages(label, scenario_description, thoughts, feelings, behaviors, image_url):
    """
    :param label: The title of the long scenario
    :param scenario_description: The text for the scenario
    :param thoughts: list of thoughts to show for long scenarios
    :param feelings: list of feelings to show for long scenarios
    :param behaviors: list of behaviors to show for long scenarios
    :return: a page group for the long scenario
    """

    pages = []
    label = label.strip()

    thoughts  = [t.strip() for t in thoughts ]
    feelings  = [f.strip() for f in feelings ]
    behaviors = [b.strip() for b in behaviors]

    with open(f"{dir_csv}/LEIA long scenarios structure.csv","r", encoding="utf-8") as csvfile:
        for i, row in enumerate(islice(csv.reader(csvfile),1,None)):

            input_1, is_image, timeout = lower(row[6]), lower(row[10]) == "true", row[13]

            title = row[0].replace("[Scenario_Name]", label)
            descr = clean_up_unicode(row[4].replace("[Scenario_Description]", scenario_description))

            text  = {"type": "Text", "text": descr}
            media = {"type": "Media", "url": lower(image_url), "border": True} if is_image else None

            show_buttons = "AfterTimeout" if timeout else "WhenComplete" if input_1 == "timedtext" else None

            if input_1 != "timedtext":
                timedtext = None
            elif "thoughts" in descr:
                timedtext = thoughts
            elif "feelings" in descr:
                timedtext = feelings
            elif "behaviors" in descr:
                timedtext = behaviors

            if timedtext: shuffle(timedtext,"long_pages")

            #input_1 is either timedtext or entry
            input = create_input(input_1, timedtext, f"long{i}")

            pages.append({
                "header_text": title,
                "header_icon": "assets/subtitle.png",
                "elements": list(filter(None,[text,media,*input])),
                **create_nav_conditions(show_buttons,timeout,[input_1])
            })

    return pages

def create_scenario_pages(domain, title, scenario_num, puzzle_text_1, word_1, comp_question,
                          answers, correct_answer, image_url, is_first, word_2=None,
                          puzzle_text_2=None, n_missing=1, include_lessons_learned=False,
                          lessons_learned_dict=None, tipe=None):

    try:
        assert correct_answer.lower() in [a.lower() for a in  answers]
    except:
        print(1)

    n_missing = lower(str(n_missing))
    pages = []

    base_name = f"{title}--{domain}".lower().replace(" ","_").replace("/","_")
    base_domain = f"{domain}".lower().replace(" ","_").replace("/","_")

    if include_lessons_learned and domain in lessons_learned_dict:  # if it should include a "lessons learned" page
        pages.append({
            "header_text": "Lessons Learned",
            "header_icon": "assets/subtitle.png",
            "elements": [
                {"type": "Text","Text": clean_up_unicode(lessons_learned_dict[domain])},
                {"type": "Entry", "name": f"lessons_learned--{base_domain}--{scenario_num}"}
            ]
        })

    if n_missing == "all" and is_first:
        # if all letters missing, and it's the first scenario, add an instructions page
        pages.append({
            "header_text": "Instructions",
            "header_icon": "assets/subtitle.png",
            "elements": [{
                "type": "Text",
                "text": "The stories you're about to see are a little bit different than ones you've "
                        "seen before. Rather than fill in missing letters to complete the final word, "
                        "we're going to challenge you to generate your own final word that will complete "
                        "the story. Your goal is to think of a word that will end the story on a "
                        "positive note. The ending doesn't have to be so positive that it doesn't "
                        "seem possible, but we want you to imagine you are handling the situation well.",
            }]
        })

    pages.append({  # adding the image page
        "header_text": title,
        "header_icon": "assets/subtitle.png",
        "elements": [
            {"type": "Text", "text": title },
            {"type": "Media", "url": lower(image_url) }
        ]
    })

    pages.append({  # adding the puzzle page
        "header_text": title,
        "header_icon": "assets/subtitle.png",
        "elements": [
            {
                "type": "Text", "text": puzzle_text_1
            },
            {
                "type": "WordPuzzle",
                "name": f"{base_name}--puzzle1",
                "correct_feedback": "Correct!",
                "incorrect_feedback": "Whoops! That doesn't look right. Please wait a moment and try again.",
                "incorrect_delay": 5000,
                "display_delay": 2000,
                "words": [word_1]
            }
        ],
        "navigation_conditions": "wait_for_correct"
    })

    if n_missing in ["1","2"]:
        pages[-1]["elements"][-1]["missing_letter_count"] = int(n_missing)
    elif n_missing == "all":
        pages[-1]["elements"][-1] = {"type": "Entry", "name": f"{base_name}--puzzle1_entry"}

    if has_value(word_2) and has_value(puzzle_text_2):
        pages.append({
            "header_text": title,
            "header_icon": "assets/subtitle.png",
            "elements": [
                {
                    "type": "Text", "text": puzzle_text_2
                },
                {
                    "type": "WordPuzzle",
                    "name": f"{base_name}--puzzle_word2".lower().replace(" ","_").replace("/","_"),
                    "correct_feedback": "Correct!",
                    "incorrect_feedback": "Whoops! That doesn't look right. Please wait a moment and try again.",
                    "incorrect_delay": 5000,
                    "display_delay": 2000,
                    "words": [word_2]
                }
            ],
            "navigation_conditions": "wait_for_correct"
        })

        if n_missing in ["1","2"]:
            pages[-1]["elements"][-1]["missing_letter_count"] = int(n_missing)
        elif n_missing == "all":
            pages[-1]["elements"][-1] = {"type": "Entry", "name": f"{base_name}--puzzle2_entry"}

    if n_missing != "all":
        pages.append({
            "header_text": title,
            "header_icon": "assets/subtitle.png",
            "elements": [
                {
                    "type": "Text", "Text": comp_question
                },
                {
                    "type": "Buttons",
                    "name": f"{base_name}--comp_question",
                    "correct_feedback": "Correct!",
                    "incorrect_feedback": "Whoops! That doesn't look right. Please wait a moment and try again.",
                    "incorrect_delay": 5000,
                    "buttons": [a.strip() for a in answers],
                    "column_count": 1,
                    "correct_value": correct_answer
                }
            ],
            "navigation_conditions":["wait_for_correct","wait_for_click"]
        })

    for page in pages:
        if tipe: page["type"] = tipe
        page["scenario_num"] = scenario_num

    return pages

def create_resource_page(tips, strategies, resources, domain):

    resource_type = choice(["Tip", "Strategy", "Resource"], "resources")

    if resource_type == "Tip":
        label,text = tips.pop(0)  # pop the first list within the lists out of tip
        tips.append([label,text])  # adding that tip back to the end of the list

        title = "Apply to Daily Life: Make It Work for You!"
        text = text
        input = {"type": "Entry", "name": f"{label}--entry".lower()}

    if resource_type == "Strategy":
        [label,text] = strategies[domain].pop(0)
        strategies[domain].append([label,text])

        title = f"Manage Your Feelings: {domain}"
        text = text
        input = None

    if resource_type == "Resource":
        [label,link,text] = resources[domain].pop(0)
        resources[domain].append([label,link,text])

        title = f"Resource: {domain}"
        text = f"{label}\n\n{text}"
        input = None

    text = { "type": "Text", "text": text }
    elements = [text,input] if input else [text]

    return {"header_text": title, "header_icon": "assets/subtitle.png", "elements": elements }

def create_discrimination_page(conditions, text, items, input_1, input_name, variable_name, title):

    text = {"type": "Text", "text": text, 'html':True}
    input = create_input(input_1, items, input_name, variable_name)

    page = {
        "header_text": title,
        "header_icon": "assets/subtitle.png",
        "elements": [text,*input],
        **create_conditions(conditions),
        **create_nav_conditions(inputs=[input_1])
    }

    return page

def create_survey_page(text=None, media=None, image_framed=None, values=None, input_type=None,
                       variable_name=None, title=None, output_name=None, show_buttons=None, 
                       condition=None, timeout=None, is_html=None):
    """
    This function creates a page with a survey question.
    :param text: Text to go on the page
    :param media: Link to image or video that should be shown on that page
    :param image_framed: True/False if the image should be framed in the middle of the page (as opposed to taking up the entire screen)
    :param items: Options for buttons, or other text options ("OtherChoices") for slider questions (usually 'Prefer not to answer')
    :param input_type:  Buttons, Picker, Checkbox, Puzzle, Entry, Slider, Scheduler
    :param variable_name: If later pages being shown depend on the answer to this page, you need to set a VariableName for it
    :param title: title of the page
    :param input_name: the name that will pair with the survey question when the participant's data from the app is downloaded. This is very important to have for each page that you want to save a participant's response to
    :param minimum: minimum value for sliders
    :param maximum: maximum value for sliders
    :param show_buttons: "WhenCorrect" if next button is shown only after the participant answers it correctly,
                         "AfterTimeout" if next button is shown after a certain time (timeout) has happened,
                         "Never" if the next button is never shown, &  the page will automatically go to next page after timeout
    :param timeout: see show_buttons "AfterTimeout"
    :return: a page for a survey question / text page
    """

    textinput  = {"type": "Text", "text": text} if has_value(text) else None
    mediainput = {"type": "Media", "url": lower(media), "border": lower(image_framed) == "true"} if media else None

    if textinput and is_html: textinput["html"] = is_html

    input = create_input(input_type, values, output_name, variable_name)
    
    page = {
        "header_text": title,
        "header_icon": "assets/subtitle.png",
        "elements": list(filter(None,[textinput, mediainput, *input])),
        **create_conditions(condition),
        **create_nav_conditions(show_buttons,timeout,[input_type])
    }

    return page

def create_resources_domain_page(domain, resource_texts):
    resource_text = '<br/><br/><br/><br/>'.join(resource_texts)
    return {
        "header_text": domain,
        "header_icon": "assets/subtitle.png",
        "elements": [ { "type": "Text", "html": True, "text": resource_text } ]
    }

def create_video_page(video_number):
    return {
        "elements": [
            {"type": "Text" , "text": "Please press play on the training video below to learn more!"},
            {"type": "Media", "url": f"/videos/video{video_number}.mp4", "border": True}
        ]
    }

def create_write_your_own_page(text, input_1, title, input_name):
    page = create_survey_page(text=text, input=input_1, title=title, output_name=input_name)
    page["header_text"] = title or "Write Your Own"
    page["header_icon"] = "assets/subtitle.png",
    return page
