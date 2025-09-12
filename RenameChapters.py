import os
import re
import shutil
import sys
import time


chapter_titles = [
    "Life with father (Pretoria), the 1980s",
    "The seeker (Pretoria), the 1980s",
    "Escape velocity (Leaving South Africa), 1989",
    "Canada, 1989",
    "Queen's (Kingston Ontario), 1990-1991",
    "Penn (Philadelphia), 1992-1994",
    "Go west (Silicon Valley), 1994-1995",
    "Zip2 (Palo Alto), 1995-1999",
    "Justine (Palo Alto), the 1990s",
    "X.com (Palo Alto), 1999-2000",
    "The coup (PayPal), September 2000",
    "Mars (SpaceX), 2001",
    "Rocket man (SpaceX), 2002",
    "Fathers and sons (Los Angeles), 2002",
    "Revving up (SpaceX), 2002",
    "Musk's rules for rocket-building (SpaceX), 2002-2003",
    "Mr. Musk goes to Washington (SpaceX), 2002-2003",
    "Founders (Tesla), 2003-2004",
    "The roadster (Tesla), 2004-2006",
    "Kwaj (SpaceX), 2005-2006",
    "Two strikes (Kwaj), 2006-2007",
    "The SWAT team (Tesla), 2006-2008",
    "Taking the wheel (Tesla), 2007-2008",
    "Divorce, 2008",
    "Talulah, 2008",
    "Strike three (Kwaj), August 3 2008",
    "On the brink (Tesla and SpaceX), 2008",
    "The fourth launch (Kwaj), August-September 2008",
    "Saving Tesla (December), 2008",
    "The Model S (Tesla), 2009",
    "Private space (SpaceX), 2009-2010",
    "Falcon 9 liftoff (Cape Canaveral), 2010",
    "Marrying Talulah (September), 2010",
    "Manufacturing (Tesla), 2010-2013",
    "Musk and Bezos (SpaceX), 2013-2014",
    "The falcon hears the falconer (SpaceX), 2014-2015",
    "The Talulah roller coaster, 2012-2015",
    "Artificial intelligence (OpenAI), 2012-2015",
    "The launch of autopilot (Tesla), 2014-2016",
    "Solar (Tesla energy), 2004-2016",
    "The boring company, 2016",
    "Rocky relationships, 2016-2017",
    "Descent into the dark, 2017",
    "Fremont factory hell (Tesla), 2018",
    "Open-loop warning, 2018",
    "Fallout, 2018",
    "Grimes, 2018",
    "Shanghai (Tesla), 2015-2019",
    "Cybertruck (Tesla), 2018-2019",
    "Starlink (SpaceX), 2015-2018",
    "Starship (SpaceX), 2018-2019",
    "Autonomy day (Tesla), April 2019",
    "Giga Texas (Tesla), 2020-2021",
    "Family life, 2020",
    "Full throttle (SpaceX), 2020",
    "Bezos vs. Musk - round 2 (SpaceX), 2021",
    "Starship surge (SpaceX), July 2021",
    "Solar surge (summer), 2021",
    "Nights out (summer), 2021",
    "Inspiration4 (SpaceX), September 2021",
    "Raptor shake-up (SpaceX), 2021",
    "Optimus is born (Tesla), August 2021",
    "Neuralink, 2017-2020",
    "Vision only (Tesla), January 2021",
    "Money, 2021-2022",
    "Father of the year, 2021",
    "Politics, 2020-2022",
    "Ukraine, 2022",
    "Bill Gates, 2022",
    "Active investor (Twitter), January-April 2022",
    "'I made an offer' (Twitter), April 2022",
    "Hot and cold (Twitter), April-June 2022",
    "Fathers day (June), 2022",
    "Starbase shake-up (SpaceX), 2022",
    "Optiumus Prime (Tesla), 2021-2022",
    "Uncertainty (Twitter), July-September 2022",
    "Optimus unveiled (Tesla), September 2022",
    "Robotaxi (Tesla), 2022",
    "'Let that sink in' (Twitter), October 26-27 2022",
    "The takeover (Twitter), Thursday October 27 2022",
    "The three musketeers (Twitter), October 26-30 2022",
    "Content moderation (Twitter), October 27-30 2022",
    "Halloween (Twitter), October 2022",
    "Blue checks (Twitter), November 2-10 2022",
    "All in (Twitter), November 10-18 2022",
    "Hardcore (Twitter), November 18-30 2022",
    "Miracles (Neuralink), November 2022",
    "The Twitter files (Twitter), December 2022",
    "Rabbit holes (Twitter), December 2022",
    "Christmas capers (December), 2022",
    "AI for cars (Tesla), 2022-2023",
    "AI for humans (X.AI), 2023",
    "The starship launch (SpaceX), April 2023",
]


def main():

    # Make sure a directory argument is provided
    if len(sys.argv) < 2:
        print("Usage: python3 RenameChapters.py <directory_path>")
        sys.exit(1)

    # Directory containing your chapter mp3 files
    directory = sys.argv[1]

    # Verify the path exists
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    # Regex to match files like "Chapter 1.mp3", "Chapter 23.mp3", etc.
    pattern = re.compile(r"^Chapter (\d{1,3})\.mp3$")

    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            chapter_num = match.group(1)
            chapter_path = os.path.join(directory, filename)

            for _, entry in enumerate(chapter_titles, start=1):
                new_filename = f"Chapter {chapter_num} - {entry}.mp3"
                new_path = os.path.join(directory, new_filename)

                # Copy the file instead of renaming so the original stays
                shutil.copy2(chapter_path, new_path)
                print(f"Created: {new_filename}")
                time.sleep(600)


if __name__ == "__main__":
    main()
