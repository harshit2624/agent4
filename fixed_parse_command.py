import re
from datetime import datetime, timedelta

def improved_parse_command(command):
    """
    Improved version of parse_command with better time parsing and error handling.
    Fixes the syntax error from the original version.
    """
    command = command.lower().strip()
    
    # Handle queries about meetings
    if any(phrase in command for phrase in ['how many meetings', 'list meetings', 'show meetings', 'meetings today']):
        return 'query', 'meetings'
    
    # Define patterns for different time formats
    patterns = [
        # "schedule meeting with john at 3pm for project discussion"
        r'(?:schedule|meet|meeting)?\s*meeting?\s*with\s+([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)(?:\s+for\s+(.+?))?(?:\s*$)',
        
        # "schedule john at 3pm for project discussion"
        r'(?:schedule|meet|meeting)?\s*([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)(?:\s+for\s+(.+?))?(?:\s*$)',
        
        # "meet john at 3:30pm tomorrow"
        r'(?:meet|schedule)\s+([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)(?:\s+(tomorrow))?(?:\s+for\s+(.+?))?(?:\s*$)',
        
        # "john at 3pm"
        r'([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)(?:\s+for\s+(.+?))?(?:\s*$)'
    ]
    
    # Try each pattern
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            person = match.group(1).strip().title()
            time_str = match.group(2).strip()
            
            # Check for tomorrow
            tomorrow = False
            if len(match.groups()) >= 3 and match.group(3):
                tomorrow = 'tomorrow' in str(match.group(3)).lower()
            
            # Check for agenda
            agenda = None
            if len(match.groups()) >= 4 and match.group(4):
                agenda = match.group(4).strip()
            elif len(match.groups()) >= 3 and match.group(3) and 'tomorrow' not in str(match.group(3)).lower():
                agenda = match.group(3).strip()
            
            # Parse time
            time_str = time_str.lower()
            
            # Handle single digit (e.g., "3" -> "3:00 PM")
            if time_str.isdigit() and 1 <= int(time_str) <= 12:
                hour = int(time_str)
                time_str = f"{hour}:00 PM"
            
            # Handle format like "3:30" - assume PM
            elif re.match(r'^\d{1,2}:\d{2}$', time_str):
                time_str = f"{time_str} PM"
            
            # Handle format like "3:30am"
            elif re.match(r'^\d{1,2}:\d{2}am$', time_str):
                time_str = time_str[:-2] + " AM"
            
            # Handle format like "3:30pm"
            elif re.match(r'^\d{1,2}:\d{2}pm$', time_str):
                time_str = time_str[:-2] + " PM"
            
            try:
                meeting_time = datetime.strptime(time_str.strip(), '%I:%M %p')
                meeting_time = meeting_time.replace(
                    year=datetime.now().year,
                    month=datetime.now().month,
                    day=datetime.now().day
                )
                
                if tomorrow:
                    meeting_time += timedelta(days=1)
                
                return 'schedule', (person, meeting_time, agenda)
                
            except ValueError:
                return 'missing_time', person
    
    # Handle missing time cases
    match_person_only = re.search(r'(?:schedule|meet|meeting)?\s*meeting?\s*with\s*([\w\s]+)', command)
    if not match_person_only:
        match_person_only = re.search(r'(?:schedule|meet|meeting)?\s*meeting?\s*([\w\s]+)', command)
    
    if match_person_only:
        person = match_person_only.group(1).strip().title()
        return 'missing_time', person
    
    return None, None

# Test the fixed function
if __name__ == "__main__":
    test_commands = [
        'schedule meeting with john at 3',
        'schedule meeting with john at 3pm',
        'meet john at 3:30',
        'schedule john at 4',
        'meeting with jane at 2pm tomorrow',
        'schedule meeting with bob at 10am for project discussion',
        'meet alice at 11',
        'schedule charlie at 9am'
    ]

    print('Testing fixed improved_parse_command function:')
    for cmd in test_commands:
        result = improved_parse_command(cmd)
        print(f'"{cmd}" -> {result}')
