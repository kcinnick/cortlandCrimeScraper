import os
from pathlib import Path


def rename_folders(root_path):
    for root, dirs, files in os.walk(root_path, topdown=False):
        # Iterate in reverse to ensure we rename child folders before their parents
        for name in dirs:
            if name.isdigit() and len(name) == 1:
                # This is a single-digit folder name, prepare new name
                new_name = f'0{name}'
                original_path = Path(root) / name
                new_path = Path(root) / new_name

                print(f'Renaming {original_path} to {new_path}')

                # Rename the folder
                original_path.rename(new_path)


def main():
    path = r'C:\Users\Nick\PycharmProjects\cortlandStandardScraper\pdfs'
    rename_folders(path)


if __name__ == '__main__':
    main()
