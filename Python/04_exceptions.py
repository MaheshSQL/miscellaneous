
# Scenario: Calculate student grades, handle invalid inputs using generic and custom exceptions

class InvalidMarksError(ValueError):

    def __init__(self, marks:int):
        self.marks = marks        
        super().__init__(f'Invalid marks enetered')

def validate_inputs(name: str, subject: str, marks: int) -> bool:
    
    if not name:
        raise ValueError('Name cannot be empty')
    
    if not subject:
        raise ValueError('Subject cannot be empty')
    
    if not marks:
        raise ValueError('Marks cannot be blank')
    
    if marks < 0 or marks > 100:
        raise InvalidMarksError(marks=marks)
    
    return True
    

def calculate_grade(name: str, subject: str, marks: int) -> str:

    grade = ''

    try:
        print(f'Grade calculation started for {name}')

        if validate_inputs(name=name, subject=subject, marks=marks):

            match marks:
                case n if n < 40:
                    grade = 'C'
                case n if 40 <= n <= 80:
                    grade = 'B'
                case n if 80 < n:
                    grade = 'A'
    
    except InvalidMarksError as ex:
        print(f'Error occured: Invalid marks {ex.marks} entered')        
        raise

    except ValueError as ex:
        print(f'Error occured: {ex}')
        raise


    finally:
        print(f'Grade calculation completed')
        
    return grade


# This will work fine
# grade = calculate_grade(name='Joe Blogs', subject='Geometry', marks=95)
# print(f'grade:{grade}')
# print()

# This will raise a ValueError
# grade = calculate_grade(name='', subject='Geometry', marks=95)
# print(f'grade:{grade}')
# print()

# This will raise InvalidMarksError
grade = calculate_grade(name='Joe Blogs', subject='Geometry', marks=195)
print(f'grade:{grade}')
print()

print('*'*20)