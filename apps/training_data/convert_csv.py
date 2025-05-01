import re
import pandas as pd

def convert_ass_to_csv(ass_path, csv_path):
    """
    Convert an .ass subtitle file into a .csv file.
    
    Parameters:
    ass_path (str): Path to the .ass file.
    csv_path (str): Path where the output .csv file will be saved.
    """
    with open(ass_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    dialogue_pattern = re.compile(r"^Dialogue:\s+\d+,(?P<start>[^,]+),(?P<end>[^,]+),(?P<style>[^,]+),(?P<name>[^,]*),[^,]*,[^,]*,[^,]*,[^,]*,(?P<text>.*)$")
    
    rows = []
    for line in lines:
        match = dialogue_pattern.match(line)
        if match:
            start_time = match.group("start")
            end_time = match.group("end")
            name = match.group("name")
            text = match.group("text").replace("\\N", " ")  # Replace line breaks in subtitles with spaces
            rows.append({
                "Start": start_time,
                "End": end_time,
                "Name": name.strip(),
                "Text": text.strip()
            })

    # Convert times to milliseconds for easier processing (optional)
    for row in rows:
        row["Start"] = convert_ass_time_to_ms(row["Start"])
        row["End"] = convert_ass_time_to_ms(row["End"])

    # Save rows to a CSV file
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)

def convert_ass_time_to_ms(ass_time):
    """
    Convert ASS time format (h:mm:ss.cs) to milliseconds.

    Parameters:
    ass_time (str): ASS time string.

    Returns:
    int: Time in milliseconds.
    """
    try:
        h, m, s = ass_time.split(":")
        s, cs = s.split(".")  # Split seconds and centiseconds
        return int(float(h) * 3600 * 1000 + float(m) * 60 * 1000 + float(s) * 1000 + float(cs) * 10)
    except ValueError as e:
        raise ValueError(f"Invalid ASS time format: {ass_time}. Expected h:mm:ss.cs") from e