from pathlib import Path
import csv
import shutil
from tqdm import tqdm
import re

def get_image_with_highest_counter(directory: Path) -> int:
    """
    Given a folder, this function finds the image with the highest counter based on the format {macro-category}{counter}.extension.
    
    :param folder: Path to the folder containing images.
    :return: The counter of the image with the highest counter.
    """
    max = -1

    # Get all files in the directory
    files = [file.name for file in directory.iterdir() if file.is_file()]

    for file in files:
        match = re.search(r"(\d+)(?=\.\w+$)", file)  # Extract image counter
        if match:
            counter = int(match.group(1))

            if counter > max:
                max = counter
    
    return max

def merge_crawled_data_per_macro_category(marketplace:str, macro_category:str, micro_category_list:list, save_path:Path, final_csv:Path) -> None:
    """
    Merge the crawled data into the given folder (save_path). Data will be divided into subfolders according to its macro-category. The mapping between image and tabular data will be stored in the final_csv file.

    :param marketplace: marketplace name from which the data has been crawled.
    :param macro_category: macro-category of the micro_category_list.
    :param micro_category_list: a list of Path objects. Each object represents a micro-category folder of the given macro-category.
    :param save_path: the folder into which merge the crawled data.
    :param final_csv: CSV file to store all mapping done during crawling.
    :return: None
    """
    counter = 0

    # Create the macro-category folder in save_path if it doesn't exist
    subfolder = save_path.joinpath(macro_category)
    if not subfolder.exists():
        subfolder.mkdir()
    else:
        # If it already exist, get the name of the last stored image
        counter = get_image_with_highest_counter(subfolder) + 1

    # Open final_csv file in append mode.
    with final_csv.open("a", newline="") as final_csv_file:
        csv_writer = csv.writer(final_csv_file)

        # For each micro-category folder.
        for micro_folder in tqdm(micro_category_list, desc=f"Processing {macro_category}", unit="folder"):
            
            # Get all the execution folders.
            execution_level = [child for child in micro_folder.iterdir() if child.is_dir()]

            # For each execution folder
            for execution_folder in tqdm(execution_level, desc=f"Processing {micro_folder.name}", unit="folder"):
                # Get images folder.
                img_path = execution_folder.joinpath("images")

                if not img_path.exists():
                    raise FileNotFoundError(f"The images folder doesn't exists! This is the path: {img_path.absolute()}")

                # Get the CSV file which maps the image with respective tabular information.
                csv_path = img_path.joinpath("image_mapping.csv")

                if not csv_path.exists():
                    raise FileNotFoundError(f"The CSV file doesn't exists! This is the path: {csv_path.absolute()}")
                
                with csv_path.open("r", newline="") as csv_micro_category:
                    csv_reader_micro = csv.reader(csv_micro_category)
                    next(csv_reader_micro) # Skip header

                    # Read all the rows in the CSV file
                    for row in csv_reader_micro:
                        # marketplace name, img name, tabular data (without web_page, url, depth_node, index_node)
                        _, img_name, tabular_data = row[0], row[1], row[6:]

                        # Get the corresponding image path
                        old_img_path = img_path.joinpath(img_name)

                        if not old_img_path.exists():
                            raise FileNotFoundError(f"There is an error in the mapping file. {old_img_path.absolute()} doesn't exists!")
                        
                        # Define the new image name and copy it
                        new_img_name = f"{macro_category}{counter}{old_img_path.suffix}"
                        new_img_path = subfolder.joinpath(new_img_name)

                        shutil.copy(old_img_path, new_img_path)

                        # Copy the row into the new CSV file with updated image name
                        csv_writer.writerow([f"{macro_category}/{new_img_name}", marketplace, *tabular_data])

                        counter += 1

def merge_crawled_data_with_no_micro_category(marketplace:str, macro_category:Path, save_path:Path, final_csv:Path) -> None:
    """
    Merge the crawled data into the given folder (save_path). This function has the same behavior as the previous one but it works for the images with no micro-category.

    :param marketplace: marketplace name from which the data has been crawled.
    :param macro_category: macro-category folder path.
    :param save_path: the folder into which merge the crawled data.
    :param final_csv: CSV file to store all mapping done during crawling.
    :return: None
    """
    counter = 0

    # Create the macro-category folder in save_path if it doesn't exist
    subfolder = save_path.joinpath(macro_category.name)
    if not subfolder.exists():
        subfolder.mkdir()
    else:
        # If it already exist, get the name of the last stored image
        counter = get_image_with_highest_counter(subfolder) + 1

    # Open final_csv file in append mode.
    with final_csv.open("a", newline="") as final_csv_file:
        csv_writer = csv.writer(final_csv_file)

        # Get the execution folders
        execution_level = [child for child in macro_category.iterdir() if child.is_dir()]

        # For each execution folder
        for execution_folder in tqdm(execution_level, desc=f"Processing {macro_category.name}", unit="folder"):
            # Get images folder.
            img_path = execution_folder.joinpath("images")

            if not img_path.exists():
                raise FileNotFoundError(f"The images folder doesn't exists! This is the path: {img_path.absolute()}")

            # Get the CSV file which maps the image with respective tabular information.
            csv_path = img_path.joinpath("image_mapping.csv")

            if not csv_path.exists():
                raise FileNotFoundError(f"The CSV file doesn't exists! This is the path: {csv_path.absolute()}")
            
            with csv_path.open("r", newline="") as csvfile:
                csv_reader = csv.reader(csvfile)
                next(csv_reader) # Skip header

                # Read all the rows in the CSV file
                for row in csv_reader:
                    # marketplace name, img name, tabular data (without web_page, url, depth_node, index_node)
                    _, img_name, tabular_data = row[0], row[1], row[6:]

                    # Get the corresponding image path
                    old_img_path = img_path.joinpath(img_name)

                    if not old_img_path.exists():
                        raise FileNotFoundError(f"There is an error in the mapping file. {old_img_path.absolute()} doesn't exists!")
                    
                    # Define the new image name and copy it
                    new_img_name = f"{macro_category.name}{counter}{old_img_path.suffix}"
                    new_img_path = subfolder.joinpath(new_img_name)

                    shutil.copy(old_img_path, new_img_path)

                    # Copy the row into the new CSV file with updated image name
                    csv_writer.writerow([f"{macro_category.name}/{new_img_name}", marketplace, *tabular_data])

                    counter += 1

if __name__ == '__main__':
    data_path = str(input("Provide the folder path in which the crawled data are stored:\n"))
    data_path = Path(data_path)

    if not data_path.exists() or not data_path.is_dir():
        raise FileNotFoundError("The folder path provided doesn't exists")
    
    merge_path = Path(str(input("Provide the folder path on which will be stored the merged data:\n")))

    merge_path.mkdir(exist_ok= True)

    # Create the CSV file with the same header as the crawled data.
    csv_merged = merge_path.joinpath("img_mapping.csv")
    if not csv_merged.exists():
        with csv_merged.open("w", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(["image_path", "marketplace", "title", "description", "vendor", "origin", "destination", "currency", "price", "cryptocurrency", "crypto_price", "macro_category", "micro_category"])


    # Get all marketplace folders.
    marketplace_level = [child for child in data_path.iterdir() if child.is_dir()]
    
    # For each marketplace
    for market_folder in marketplace_level:

        # For each marketplace, get all the macro-category folders.
        macro_category_level = [child for child in market_folder.iterdir() if child.is_dir()]

        # For each macro-category
        for macro_folder in macro_category_level:
        
            if "steroids" in macro_folder.name:
                # This product has no micro-category
                merge_crawled_data_with_no_micro_category(market_folder.name, macro_folder, merge_path, csv_merged)
            else:
                # Get all the micro-category folders.
                micro_category_level = [child for child in macro_folder.iterdir() if child.is_dir()]

                merge_crawled_data_per_macro_category(market_folder.name, macro_folder.name, micro_category_level, merge_path, csv_merged)
