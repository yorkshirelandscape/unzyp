import os
import re
import zipfile
import shutil
import datetime
from pathlib import Path

LCASE_TITLE_WORDS = ["a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "is", "it", "of", "on", "or", "the", "to"]

event_log = {} # List to store event logs

def log_event(content_id, message, file=None, event_type="event", log=event_log):
    """
    Log an event to a list of dicts, one per content_id, each containing an array of events
    and an array of files generated. Each even will include a timestamp, and message. The
    contents of the log will be printed to the console at the end of the script.
    """
    log |= {
        content_id: {
            "contents": None,
            "destination": None,
            "files": [str(file)] if file else [],
            "events": [{
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": event_type,
                "file": file,
                "message": message,
            }]
        }
    }

def mkdirmv(src, dst):
    """
    Move a file or directory from src to dst, creating any necessary intermediate directories along the way.
    """
    for path in [src, dst]:
        if isinstance(path, str):
            path = Path(path)
    os.makedirs(dst.parent, exist_ok=True)
    shutil.move(src, dst)

def get_filepath(content_id, product_line_slug, ext):
    # Convert PascalCase or words without spaces to have spaces between them
    def insert_spaces(text):
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', 
                    re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', 
                        re.sub(r'([0-9]+)([a-zA-Z])', r'\1 \2', text)))
    
    root = content_id[:4]
    root_dir = Path(f"{root + 'finder 2e'}/")
    [pl_dir, season, scenario, prefix, title] = [None] * 5
    if product_line_slug == "finderAdventurePath":
        return False
    elif product_line_slug == "finderQuestSeries2":
        pl_dir = root_dir / "Quests S2"
        season = "Q"
        scenario = re.search(r"(?<=finderQuestSeries2)([0-9]+)", content_id).group(1)
        prefix = f"{season}{scenario} - "
        ss = f"{root + product_line_slug}{scenario}"
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(ss, '', content_id)))
    elif product_line_slug == "finderPlaytestScenario":
        pl_dir = root_dir / "Playtest"
        season = "P"
        scenario = re.search(r'([0-9]+)', content_id).group(1)
        prefix = f"{scenario} - "
        ss = f"{root + product_line_slug}{scenario}"
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(ss, '', content_id)))
    elif product_line_slug == "finderQuest":
        product_line_slug = "PathfinderQuestSeries1" if root == "Path" else "StarfinderQuest"
        pl_dir = root_dir / ("Quests S1" if root == "Path" else "Quests")
        season = "Q"
        scenario = re.search(r'([0-9]+)', content_id).group(1)
        prefix = f"{season}{scenario} - "
        ss = f"{root + product_line_slug}{scenario}"
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(ss, '', content_id)))
    elif product_line_slug == "finderBounty":
        pl_dir = root_dir / "Bounties"
        season = "B"
        scenario = re.search(r'([0-9]+)', content_id).group(1)
        prefix = f"{season}{scenario} - "
        ss = f"{root + product_line_slug}{scenario}"
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(ss, '', content_id)))
    elif product_line_slug == "finderSocietyScenario":
        season, dash, scenario = re.search(r'([0-9]+)(-|–|—)([0-9][0-9])', content_id).groups()
        pl_dir = root_dir / f"{root}finder Society/S{season.zfill(2)}"
        prefix = f"{season}-{scenario} - "
        ss = f"{root + product_line_slug}{season}{dash}{scenario}"
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(ss, '', content_id)))
    elif product_line_slug in ["finderFlip-Mat", "finderFlip-Tiles"]:
        pl_dir = root_dir / "Maps" / insert_spaces(root + product_line_slug)
        prefix = ""
        ss = f"{root + product_line_slug}"
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(ss, '', content_id)))
    else:
        pl_dir = root_dir / "Reference"
        prefix = ""
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(r"(Star|Path)finder", "", content_id)))

    return (pl_dir or Path(".")) / f"{prefix}{title}{ext}"

def process_file(file_path, zip_path):
    if isinstance(file_path, str):
        file_path = Path(file_path)
    if not file_path.is_file():
        # print(f"File {file_path} does not exist.")
        log_event(zip_path.stem, f"File {file_path} does not exist.", file_path, "error")
        return
    content_id = zip_path.stem
    ext = file_path.suffix
    product_line_slug = next((pl for pl in [
        "finderSocietyScenario",
        "finderQuestSeries2",
        "finderQuest",
        "finderAdventurePath",
        "finderBounty",
        "finderFlip-Mat",
        "finderFlip-Tiles",
        "finderPlaytestScenario",
        "finderAdventure",
        "finderOne-Shot",
    ] if pl in content_id), None)
    if not product_line_slug:
        product_line_slug = re.search(r"finder[0-9a-zA-Z-]+(?=PDF|\.)", content_id).group(0)
    elif product_line_slug == "finderAdventurePath":
        print(f"Adventure Path zip file detected: {zip_path}, skipping.")
        return
    else:
        new_path = get_filepath(content_id, product_line_slug, ext)
        mkdirmv(file_path, new_path)
        # print(f"Renamed file to: {new_path}")
        log_event(zip_path.stem, f"Created file: {new_path}", file=new_path)
        return new_path

def process_zip(zip_path):
    if isinstance(zip_path, str):
        zip_path = Path(zip_path)
    if not zip_path.is_file():
        # print(f"File {zip_path} does not exist.")
        log_event(zip_path.stem, f"File {zip_path} does not exist.", file=None, event_type="error")
        return

    temp_dir = zip_path.parent / f"temp_{os.urandom(4).hex()}"
    temp_dir.mkdir()

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        file_paths = list(temp_dir.rglob("*.pdf"))
        other_files = [f for f in list(temp_dir.rglob("*")) if f.is_file() and f.suffix != ".pdf"]
        ext_dirs = [f for f in list(temp_dir.rglob("*")) if f.is_dir()]
        
        if file_paths:
            file_dir = file_paths[0].parent
            for file_path in file_paths:
                pdf_path = process_file(file_path, zip_path)
                if pdf_path:
                    pdfname = pdf_path.stem
                    filename_root = pdfname.split(" - ")[0]
            if other_files:
                for other_file in other_files:
                    filename = filename_root + " - " + other_file.name
                    new_path = file_dir / filename
                    mkdirmv(other_file, new_path)
                    log_event(zip_path.stem, f"Moved file: {new_path}", file=new_path)
            if ext_dirs:
                for ext_dir in ext_dirs:
                    new_path = file_dir / ext_dir.name
                    mkdirmv(ext_dir, new_path)
                    # print(f"Moved directory {ext_dir} to {new_path}")
                    log_event(zip_path.stem, f"Moved directory to {new_path}", file=new_path)
        elif other_files or ext_dirs:
            mkdirmv(temp_dir, zip_path.parent / zip_path.stem)
            # print(f"No PDF. Moved extracted files to {zip_path.parent}/{zip_path.stem}.")
            log_event(zip_path.stem, f"No PDF. Moved extracted files to {zip_path.parent}/{zip_path.stem}.", file=zip_path.parent / zip_path.stem)
        else:
            print(f"No PDF or other files found in {zip_path}, skipping.")
            log_event(zip_path.stem, f"No PDF or other files found in {zip_path}, skipping.", file=None, event_type="error")
                
    finally:
        if temp_dir.is_dir():
            shutil.rmtree(temp_dir)

def process_adventure_paths(ap_list):
    bookpaths = []
    for ap_zip in ap_list:
        ap_zip = Path(ap_zip)
        content_id = ap_zip.stem
        root = content_id[:4]
        pl_slug = root + "finderAdventurePath"
        ap_number = re.search(r'AdventurePath(\d+)', content_id).group(1)
        book_info = re.search(r'(\d+of\d+)', content_id, re.IGNORECASE).group(1).lower()
        remainder = re.sub(r'AdventurePath\d+|(\d+of\d+)', '', content_id)
        book_number, total_books = book_info.split('of')
        bookpath_name = content_id
        for elem in [pl_slug, ap_number, book_info, remainder]:
            bookpath_name = bookpath_name.replace(elem, "")
        bookpath_name = re.sub(r'([a-zAI])([A-Z])', r'\1 \2',
                            re.sub(r"(?<=[a-z])S(?=[A-Z])", "s", 
                                re.sub(r"[0-9][Oo]f[0-9].*", "", bookpath_name))).strip()
        bp = {
            "bp_name": bookpath_name,
            "book_number": int(book_number),
            "total_books": int(total_books),
            "ap_number": int(ap_number),
            "content_id": content_id,
            "system": root + "finder 2e",
            "ap_name": None,
            "book_name": None,
            "ap_dst": None,
            "bkzip": ap_zip,
        }
        bookpaths.append(bp)

    bp_len = len(bookpaths)
    advpths = {}
    spins = 0
    while len(bookpaths) > 0 and spins <= bp_len:
        spins += 1
        bp = bookpaths[0]
        ap_range = range( bp["ap_number"] - bp["book_number"] + 1, bp["ap_number"] + bp["total_books"] - 1 )
        ap_candidates = [vol["bp_name"] for vol in bookpaths if vol["ap_number"] in ap_range] # and vol["ap_number"] != bp["ap_number"]]
        ap_name = None
        aps_path = Path(bp["system"] + "/" + "Adventure Paths")
        os.makedirs(aps_path, exist_ok=True)
        if ap_candidates:
            name_arr = [w for w in bp["bp_name"].split(" ") if w != ""]
            matches = 999
            ap_name = ""
            ap_name_test = ""
            while matches > 1:
                for i in range( - 1, len(name_arr) * -1, -1):
                    ap_name_test = name_arr[i] + ( " " + ap_name if len(ap_name) else "" )
                    matches = len([vol for vol in ap_candidates if ap_name_test in vol])
                    ap_name = ap_name_test if matches > 1 else ap_name
        if not ap_name:
            existing_aps = [ap for ap in aps_path.iterdir() if ap.is_dir()]
            if existing_aps:
                ap_name = existing_aps[0].name
                for dir in existing_aps:
                    if dir.name in bp["bp_name"]:
                        ap_name = dir.name
                        break
        if ap_name:
            ap_name = ap_name.strip()
            advpths[ap_name] = sorted([bk for bk in bookpaths if ap_name in bk["bp_name"]], key=lambda x: x["book_number"])
            for bk in advpths[ap_name]:
                bk["ap_name"] = ap_name
                bk["book_name"] = bk["bp_name"].replace(ap_name, "").strip()
            bookpaths = [bk for bk in bookpaths if bk["ap_name"] is None]
        else:
            # print(f"Could not find a matching Adventure Path name for {bp['bp_name']}.")
            log_event(bp["content_id"], f"Could not find a matching Adventure Path name for {bp['bp_name']}.", file=None, event_type="error")
            bookpaths = bookpaths[1:]
    if not advpths:
        print("No Adventure Paths found.")
        return
                
    for ap_name, books in advpths.items():
        ap_folder = aps_path / books[0]["ap_name"]
        os.makedirs(ap_folder, exist_ok=True)
        for bk in books:
            bkzip = bk["bkzip"]
            temp_dir = ap_folder / f"temp_{os.urandom(4).hex()}"
            temp_dir.mkdir()
            book_number = bk["book_number"]
            total_books = bk["total_books"]
            content_id = bk["content_id"]
            book_info = str(book_number) + "of" + str(total_books)
            ap_number = bk["ap_number"]
            if not bkzip.is_file():
                print(f"File {str(bkzip)} does not exist.")
                continue

            try:
                with zipfile.ZipFile(bkzip, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                file_paths = list(temp_dir.rglob("*.pdf"))
                other_files = [f for f in list(temp_dir.rglob("*")) if f.is_file() and f.suffix != ".pdf"]
                ext_dirs = [f for f in list(temp_dir.rglob("*")) if f.is_dir()]
                if file_paths:
                    file_dir = file_paths[0].parent
                    for file_path in file_paths:
                        pdfname = f"{ap_name} - {book_info} - {bk["book_name"]}{" - Maps" if "InteractiveMaps" in file_path.name else ""}.pdf"
                        new_path = ap_folder / pdfname
                        mkdirmv(file_path, new_path)
                        # print(f"Created PDF: {new_path}")
                        log_event(bk["content_id"], f"Created PDF: {new_path}", file=new_path)
                    if other_files:
                        for other_file in other_files:
                            filename = f"{ap_name} - {book_info} - {other_file.name}"
                            new_path = file_dir / filename
                            mkdirmv(other_file, new_path)
                            # print(f"Created file: {new_path}")
                            log_event(bk["content_id"], f"Created file: {new_path}", file=new_path)
                    if ext_dirs:
                        for ext_dir in ext_dirs:
                            new_path = file_dir / ext_dir.name
                            mkdirmv(ext_dir, new_path)
                            # print(f"Created directory {ext_dir} at {new_path}")
                            log_event(bk["content_id"], f"Created directory {ext_dir} at {new_path}", file=new_path)
                elif other_files or ext_dirs:
                    for df in ext_dirs + other_files:
                        mkdirmv(df, ap_folder / bkzip.stem)
                    # print(f"No PDF. Moved extracted files to {ap_folder}/{bkzip.stem}.")
                    log_event(bk["content_id"], f"No PDF. Moved extracted files to {ap_folder}/{bkzip.stem}.", file=ap_folder / bkzip.stem)
                else:
                    # print(f"No PDF or other files found in {bkzip}, skipping.")
                    log_event(bk["content_id"], f"No PDF or other files found in {bkzip}, skipping.", file=None, event_type="error")
            except zipfile.BadZipFile:
                # print(f"Bad zip file: {bkzip}, skipping.")
                log_event(bk["content_id"], f"Bad zip file: {bkzip}, skipping.", file=None, event_type="error")
            except Exception as e:
                # print(f"Error processing {bkzip}: {e}")
                log_event(bk["content_id"], f"Error processing {bkzip}: {e}", file=None, event_type="error")

            finally:
                shutil.rmtree(temp_dir)

if __name__ == "__main__":
    base_dir = Path(".")
    zip_path = base_dir / "ZIPs"
    if zip_path.is_dir():
        zip_dir = Path(zip_path)
        zip_list = list(zip_dir.rglob("*.zip"))
        ap_list = [str(z) for z in zip_list if "finderAdventurePath" in z.name]
    else:
        zip_list = []
        ap_list = []
        print(f"Directory {zip_path} does not exist or is not a directory.")
    if ap_list:
        process_adventure_paths(ap_list)
        zip_list = [z for z in zip_list if "finderAdventurePath" not in z.name]
    if zip_list:
        for zip_file in zip_list:
            if zip_file not in ap_list:
                process_zip(zip_file)
    if event_log:
        print("\nEvent Log:")
        for content_id, details in event_log.items():
            print(f"Content ID: {content_id}")
            print(f"  Contents: {re.search( r"[^\\\/]+(?=\.[a-zA-Z]+$)", details['files'][0] ).group(0) if details['files'] else None}")
            print(f"  Destination: {re.search( r"^.+[\\\/](?=[^\\\/]+$)", details['files'][0] ).group(0) if details['files'] else None}")
            print(f"  Files: {set(details['files'])}")
            for e in details["events"]:
                print(f"    Timestamp: {e['timestamp']}")
                print(f"    Event Type: {e['event_type']}")
                print(f"    File: {e['file']}")
                print(f"    Message: {e['message']}")
            print()
        
