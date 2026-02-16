import csv
import shutil
import time
from urllib import request
from pathlib import Path
from itertools import islice

dir_root = "./make"
dir_csv  = f"{dir_root}/CSV"

with open(f"{dir_csv}/images.csv", "r", encoding="utf-8") as read_obj:
    for row in islice(csv.reader(read_obj), 1, None):
        url,name = row
        try:
            if "/view" in url:
                #e.g., https://drive.google.com/file/d/1agACToHkWhDmNIHThNfXgoaZQzoBzUw1/view?usp=drive_link
                start_index = url.index("/d/") + 3
                end_index = url.index("/view")
            else:
                #e.g., https://drive.google.com/file/d/1agACToHkWhDmNIHThNfXgoaZQzoBzUw1/view?usp=drive_link
                start_index = url.index("id=") + 3
                end_index = url.index("&usp")

            image_id = url[start_index:end_index]

            if not Path(f"./src/images/{name}").exists():
                time.sleep(1)
                with request.urlopen(f"https://drive.usercontent.google.com/u/1/uc?id={image_id}&export=download") as r:
                    with open(f"./src/images/{name}", mode="wb+") as f:
                        shutil.copyfileobj(r,f)
        except (KeyboardInterrupt,FileNotFoundError):
            raise
        except Exception as e:
            print("-----------------------------------")
            print(str(e))
            print(name)
            print(url)