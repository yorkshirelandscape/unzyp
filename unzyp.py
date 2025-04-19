import os
import re
import zipfile
import shutil
from pathlib import Path

def mkdirmv(src, dst):
    """
    Move a file or directory from src to dst, creating any necessary intermediate directories along the way.
    """
    for path in [src, dst]:
        if isinstance(path, str):
            path = Path(path)
    os.makedirs(dst.parent, exist_ok=True)
    shutil.move(src, dst)

def get_filepath(content_id, product_line_slug):
    # Convert PascalCase or words without spaces to have spaces between them
    def insert_spaces(text):
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', re.sub(r'([0-9]+)([a-zA-Z])', r'\1 \2', text)))
    
    root = content_id[:4]
    root_dir = f"{root + 'finder 2e'}/"
    if product_line_slug == "finderQuestSeries2":
        pl_dir = root_dir + "Quests S2/"
        season = "Q"
        scenario = re.match(r'([0-9]+)', content_id).group(1)
        prefix = f"{season}{scenario} - "
        title = insert_spaces(re.sub(r'(PDF-.*|Download)$', '', re.sub(r'^[0-9]+', '', content_id)))
    if product_line_slug == "finderQuest":
        pl_dir = root_dir + ("Quests S1" if root == "Path" else "Quests")
        season = "Q"
        scenario = re.match(r'([0-9]+)', content_id).group(1)
        prefix = f"{season}{scenario} - "
        title = insert_spaces(re.sub(r'^[0-9]+', '', content_id))
    elif product_line_slug == "finderBounty":
        pl_dir = root_dir + "Bounties"
        season = "B"
        scenario = re.match(r'([0-9]+)', content_id).group(1)
        prefix = f"{season}{scenario} - "
        title = insert_spaces(re.sub(r'^[0-9]+', '', content_id))
    elif product_line_slug == "finderSocietyScenario":
        season, scenario = re.match(r'([0-9]+)-([0-9]+)', content_id).groups()
        pl_dir = root_dir + root + "finder Society/S" + season.zfill(2)
        prefix = f"{season}-{scenario} - "
        title = insert_spaces(re.sub(r'^[0-9]+-[0-9]+', '', content_id))
    elif product_line_slug in ["PathfinderFlip-Mat", "PathfinderFlip-Tiles"]:
        title = insert_spaces(content_id)
        prefix = ""
    elif product_line_slug == "finderAdventurePath":
        return "AP"
    else:
        raise ValueError(f"Unknown product line slug: {product_line_slug}")

    return f"{pl_dir}{prefix}{title}.pdf"

def process_zip(zip_path):
    if not zip_path.is_file():
        print(f"File {zip_path} does not exist.")
        return

    temp_dir = Path(zip_path.parent) / f"temp_{os.urandom(4).hex()}"
    temp_dir.mkdir()

    def process_pdf(pdf_file):
        content_id = zip_path.stem
        product_line_slug = next((pl for pl in [
            "finderSocietyScenario",
            "finderQuest",
            "finderQuestSeries2",
            "finderAdventurePath",
            "finderBounty",
            "finderFlip-Mat",
            "finderFlip-Tiles"
        ] if pl in content_id), None)
        if not product_line_slug:
            print(f"Unknown product line slug for {zip_path}, skipping.")
            return
        elif product_line_slug == "finderAdventurePath":
            print(f"Adventure Path zip file detected: {zip_path}, skipping.")
            return
        else:
            new_pdf_path = get_filepath(content_id, product_line_slug)
            
            mkdirmv(pdf_file, new_pdf_path)
            print(f"Renamed PDF to: {new_pdf_path}")
            return new_pdf_path

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        pdf_files = list(temp_dir.rglob("*.pdf"))
        other_files = [f for f in list(temp_dir.rglob("*")) if f.is_file() and f.suffix != ".pdf"]
        ext_dirs = [f for f in list(temp_dir.rglob("*")) if f.is_dir()]
        
        if pdf_files:
            for pdf_file in pdf_files:
                pdf_path = Path(process_pdf(pdf_file))
                if pdf_path:
                    file_dir = pdf_path.parent
                    pdfname = pdf_path.stem
                    filename_root = pdfname.split(" - ")[0]
                if pdf_path and other_files:
                    for other_file in other_files:
                        filename = filename_root + " - " + other_file.name
                        new_path = file_dir / filename
                        mkdirmv(other_file, new_path)
                if pdf_path and ext_dirs:
                    for ext_dir in ext_dirs:
                        new_path = file_dir / ext_dir.name
                        mkdirmv(ext_dir, new_path)
                        print(f"Moved directory {ext_dir} to {new_path}")
        elif other_files or ext_dirs:
            mkdirmv(temp_dir, zip_path.parent / zip_path.stem)
            print(f"No PDF. Moved extracted files to {zip_path.parent}/{zip_path.stem}.")
        else:
            print(f"No PDF or other files found in {zip_path}, skipping.")
                
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
        book_info = re.search(r'(\d+of\d+)', content_id).group(1)
        remainder = re.sub(r'AdventurePath\d+|(\d+of\d+)', '', content_id)
        book_number, total_books = book_info.split('of')
        bookpath_name = content_id
        for elem in [pl_slug, ap_number, book_info, remainder]:
            bookpath_name = bookpath_name.replace(elem, "")
        bookpath_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', bookpath_name).strip()
        bp = {
            "bp_name": bookpath_name,
            "book_number": int(book_number),
            "total_books": int(total_books),
            "ap_number": int(ap_number),
            "content_id": content_id,
            "system": root + "finder 2e",
            "ap_name": None,
        }
        bookpaths.append(bp)

    bp_len = len(bookpaths)
    adv_paths = {}
    spins = 0
    while len(bookpaths) > 0 and spins <= bp_len:
        spins += 1
        bp = bookpaths[0]
        ap_range = range( bp["ap_number"] - bp["book_number"] + 1, bp["ap_number"] + bp["total_books"] - 1 )
        ap_candidates = [vol["bp_name"] for vol in bookpaths if vol["ap_number"] in ap_range and vol["ap_number"] != bp["ap_number"]]
        ap_name = None
        if ap_candidates:
            name_arr = [w for w in bp["bp_name"].split(" ") if w != ""]
            matches = 999
            ap_name = ""
            while matches > 0:
                for i in range(len(name_arr) - 1, 0, -1):
                    matches = len([vol for vol in ap_candidates if (name_arr[i] + " " if ap_name else name_arr[i]) in vol])
                    ap_name = name_arr[i] + " " + ap_name
        if ap_name:
            ap_name = ap_name.strip()
            bp["ap_name"] = ap_name
            adv_paths[ap_name] = sorted([bk for bk in bookpaths if ap_name in bk["bp_name"]], key=lambda x: x["book_number"])})
            bookpaths = [bk for bk in bookpaths if ap_name not in bk["bp_name"]]

    for ap_name, books in adv_paths.items():
        ap_folder = Path(f"{books[0]['system']}/{ap_name}")
        os.makedirs(ap_folder, exist_ok=True)
        for bk in books:
            bkzip = [bz for bz in ap_list if bk["content_id"] in bz.name].pop(0)
            temp_dir = ap_folder / f"temp_{os.urandom(4).hex()}"
            temp_dir.mkdir()

        try:
            with zipfile.ZipFile(ap_zip, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            pdf_files = list(temp_dir.rglob("*.pdf"))
            if not pdf_files:
                print(f"No PDF file found in {ap_zip}, skipping.")
                continue

            pdf_file = pdf_files[0]
            maps_suffix = "-Maps" if "InteractiveMaps" in pdf_file.name else ""

            book_name_match = re.search(book_info + r'(.*)', content_id)
            book_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', book_name_match.group(1)).strip() if book_name_match else "UnknownBook"

            new_pdf_name = f"{ap_name}-{book_number}of{total_books}-{book_name}{maps_suffix}.pdf"
            new_pdf_path = ap_folder / new_pdf_name
            mkdirmv(pdf_file, new_pdf_path)
            print(f"Renamed PDF to: {new_pdf_path}")

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
        
