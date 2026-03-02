import json
import csv

with open('CDC/school_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

rows = []
rows.append(["Cycle", "Classe", "Matière", "Chapitre", "Sous-chapitre (Titre)", "Type", "Nombre de questions", "Lien (href)"])

if "levels" in data:
    for group_name, classes in data["levels"].items():
        for cls in classes:
            class_name = cls.get("name", "")
            for subject in cls.get("subjects", []):
                subject_name = subject.get("name", "")
                for chapter in subject.get("chapters", []):
                    chapter_title = chapter.get("title", "")
                    for subchapter in chapter.get("subchapters", []):
                        sub_title = subchapter.get("title", "")
                        sub_type = subchapter.get("type", "")
                        sub_qcount = str(subchapter.get("question_count", ""))
                        sub_href = subchapter.get("href", "")
                        rows.append([group_name, class_name, subject_name, chapter_title, sub_title, sub_type, sub_qcount, sub_href])

with open('CDC/school_data.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerows(rows)

print(f"Extraction terminée. {len(rows)-1} lignes exportées.")
