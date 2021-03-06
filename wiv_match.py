import sys
import csv
import re

REGGIE = re.compile(r'\(GMT\s*(?P<sign>[\+\-])(?P<hour>[0-9]+):.*\)')

def get_gmt_hour_diff(time_zone):
    """
    Converts the time zone listing to a time zone string which only contains the 
    GMT +/- <hours>

    Floors any half-hour increments

    returns the hour difference as an int
    """
    if time_zone.startswith("(GMT)"):
        return 0
    else:
        match = REGGIE.search(time_zone)
        hours = int(match.group("hour"))
        if match.group("sign") == '-':
            hours *= -1
        return hours

def convert_csv(csv_path):
    """
    converts csv into a list of dictionaries
    """
    data = []
    with open(csv_path, "r", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        column_names = next(reader) # NOTE: the first row has column names
        for row in reader:
            datum = {}
            for col_index, col in enumerate(row):
                datum[column_names[col_index]] = col

            data.append(datum)

    return data

def make_row(mentor_datum, mentor_columns, mentee_datum, mentee_columns):
    row = []
    for mentor_column in mentor_columns:
        row.append(mentor_datum.get(mentor_column, ""))
    for mentee_column in mentee_columns:
        row.append(mentee_datum.get(mentee_column, ""))

    return row

def main(argv):
    if len(argv) == 3:
        mentors_path = sys.argv[1]
        mentees_path = sys.argv[2]
    elif len(argv) == 2 and (argv[1] == "-h" or argv[2] == "--help"):
        print("Usage: wiv_match.py <mentors_path> <mentees_path>")
        return
    else:
        mentors_path = "./Mentors.csv"
        mentees_path = "./Mentees.csv"

    max_mentee_string = "How many mentees would you be willing to take on? (The expectation is only a 1-hour meeting per mentee and any further communication is entirely up to you.)"

    mentors_data = convert_csv(mentors_path)
    mentees_data = convert_csv(mentees_path)

    mentor_uid_to_data = {}
    mentee_uid_to_data = {}

    timezone_to_mentors = {}
    field_to_mentors = {}
    mentor_to_mentees = {}

    time_zone_buffer = 12
    for mentor_datum in mentors_data:
        mentor_uid_to_data[mentor_datum["Email"]] = mentor_datum

        raw_time_zone = mentor_datum["Time Zone"]
        # NOTE: give the time zone some wiggle room
        gmt_diff = get_gmt_hour_diff(raw_time_zone)
        for time_zone in range(gmt_diff - time_zone_buffer, gmt_diff + time_zone_buffer + 1):
            mentors_in_timezone = timezone_to_mentors.get(time_zone, set())
            mentors_in_timezone.add(mentor_datum["Email"])
            timezone_to_mentors[time_zone] = mentors_in_timezone

        field = mentor_datum["How are you involved in the industry?"]
        mentors_in_field = field_to_mentors.get(field, set())
        mentors_in_field.add(mentor_datum["Email"])
        field_to_mentors[field] = mentors_in_field

        mentor_to_mentees[mentor_datum["Email"]] = []


    unmatched_mentees = []
    for mentee_datum in mentees_data:
        mentee_uid_to_data[mentee_datum["Email"]] = mentee_datum

        # NOTE: find a matching mentor
        raw_time_zone = mentee_datum["Time Zone"]
        time_zone = get_gmt_hour_diff(raw_time_zone)
        mentors_in_timezone = timezone_to_mentors.get(time_zone, set())

        field = mentee_datum["Primary Involvement: How are you involved in the industry?"]
        mentors_in_field = field_to_mentors.get(field, set())

        matching_mentors = mentors_in_field.intersection(mentors_in_timezone)

        if len(matching_mentors) > 0:
            # NOTE: sort the matching mentors to give the mentors with the least mentees a new mentee first
            mentee_counts = []
            for mentor in matching_mentors:
                mentee_count = len(mentor_to_mentees[mentor])
                mentee_counts.append((mentor, mentee_count))

            mentee_counts.sort(key=lambda x: x[1])

            for mentor, count in mentee_counts:
                raw_max_count = mentor_uid_to_data[mentor].get(max_mentee_string, 1)
                # NOTE: clean up the raw_max_count
                if raw_max_count == '':
                    max_count = 1
                else:
                    max_count = int(raw_max_count)
                if (count < max_count) and (mentor != mentee_datum["Email"]):
                    mentor_to_mentees[mentor].append(mentee_datum["Email"])
                    break
            else:
                unmatched_mentees.append(mentee_datum)
        else:
            unmatched_mentees.append(mentee_datum)

    mentor_columns = [
        "Name (First)",
        "Name (Last)",
        "Email",
        "Gender",
        "Ethnicity",
        "Social Media: Where can we find out more about you? LinkedIn*",
        "Mentorship Matchup: Tell us a little about yourself so we can find you the perfect match",
        "Country (Country)",
        "Time Zone",
        "What is your preferred language to use with your mentor/mentee? Is there another language that you would be comfortable using? If we can't find a match in your choice English will be the default.",
        "Which best describes your current career stage in the voice industry",
        "How are you involved in the industry?",
        "How many mentees would you be willing to take on? (The expectation is only a 1-hour meeting per mentee and any further communication is entirely up to you.)",
        "Meeting Topic: Is there anything in particular you'd like to discuss?",
        "Anything else you would like to tell us? A request to be paired with someone with special traits?",
        "Last Thoughts?  Work issues Public Speaking Education and experience development",
        "Negotiation Job Hunting Networking",
        "Crisis/Conflict Management",
        "Portfolios and Profiles Technical/Development/Programming",
        "Product development",
        "Confidence building",
        "Feeling stuck",
        "General Professionalism",
        "Conversational/Voice UI design",
        "NLP"
    ]
    mentee_columns = [
        "Name (First)",
        "Name (Last)",
        "Email",
        "Gender",
        "Ethnicity",
        "Social Media: Where can we find out more about you? LinkedIn",
        "Social Media: Where can we find out more about you? Personal Website/Portfolio",
        "Mentorship Matchup: Tell us a little about yourself so we can find you the perfect match",
        "Country (Country)",
        "Time Zone",
        "Stage: Which best describes your current career stage in the voice industry",
        "Primary Involvement: How are you involved in the industry?",
        "Meeting Topic: Is there anything in particular you'd like to discuss?",
        "Anything else you would like to tell us? A request to be paired with someone with special traits?",
        "Last thoughts?"
    ]
    with open('matches.csv', 'w', encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(mentor_columns + mentee_columns)

        unmatched_mentors = []
        for mentor in mentor_to_mentees:
            mentor_datum = mentor_uid_to_data[mentor]
            mentees = mentor_to_mentees[mentor]
            if len(mentees) == 0:
                unmatched_mentors.append(mentor_datum)
            else:
                for mentee in mentees:
                    mentee_datum = mentee_uid_to_data[mentee]
                    row = make_row(mentor_datum, mentor_columns, mentee_datum, mentee_columns)
                    writer.writerow(row)

        for unmatched_mentor in unmatched_mentors:
            row = make_row(unmatched_mentor, mentor_columns, {}, mentee_columns)        
            writer.writerow(row)
        for unmatched_mentee in unmatched_mentees:
            row = make_row({}, mentor_columns, unmatched_mentee, mentee_columns)        
            writer.writerow(row)

if __name__ == "__main__":
    main(sys.argv)
