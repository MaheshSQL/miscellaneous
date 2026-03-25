# Everything in Python is an object, including numbers, strings, functions, and even classes.

# Variables are references to objects in memory. When you assign a value to a variable, you are creating a reference to an object, not copying the object itself.

string_var = 'Hello, World!'
print(type(string_var))

string_var = 123
print(type(string_var))

print('*'*20)

# Annotations are a way to provide hints about the types of variables, function parameters, and return values. 
# They are not enforced by the Python interpreter (they are optional) but can be used by tools like type checkers and IDEs to catch potential type-related issues.
# Also called type hints, they can improve code readability and help developers understand the expected types of variables and function parameters.
# They do not provide any runtime impact!

def greet(name: str) -> str:
    return f'Hello, {name}!'
print(greet('Alice'))
print('*'*20)

# CLass
# Classes should be named using CapWord convention, where each word starts with a capital letter and there are no underscores between words. 
# This convention helps to distinguish class names from variable and function names, which typically use lowercase letters and underscores (snake_case). 
# For more info on class syntax: https://docs.python.org/3/tutorial/classes.html#class-definition-syntax


class Calculator:

    # Methods in a class have a required first parameter, conventionally named self, which refers to the instance of the class. 
    # This allows methods to access and modify the attributes of the instance.
    def __init__(self, brand: str):
        self.brand = brand

    # Provide method documentation using docstrings, which are enclosed in triple quotes and describe the purpose and usage of the method.
    '''Adds two numbers and returns the result.'''
    def add(self, a: float, b: float) -> float:
        return a + b 
    
    '''Subtracts the second number from the first and returns the result.''' 
    def subtract(self, a: float, b: float) -> float:
        return a - b
    
calc = Calculator(brand='Casio')
calc.c = 10 # You can add attributes to an instance of a class at runtime, which is a feature of Python's dynamic nature. However, this practice is generally discouraged as it can lead to code that is difficult to understand and maintain. It can also cause issues if other parts of the code expect the class to have a certain structure or set of attributes. It's usually better to define all necessary attributes within the class definition to ensure consistency and clarity in your code.

print(f'Adding 5 and 3 gives: {calc.add(5, 3)} ')
print(f'Calc.c value: {calc.c}')
# print(calc.subtract(5, 3))
print('*'*20)

# Composition
# Composition is a design principle in object-oriented programming where a class is composed of one or more objects from other classes, rather than inheriting from them. 
# This allows for greater flexibility and modularity in code design, as it promotes the idea of "has-a" relationships between objects, rather than "is-a" relationships.

class Wheel:
    def __init__(self, size: int):
        
        # Public attributes
        self.size = size
        
        # Prefix non-public attributes or method with a single underscore to indicate that they are intended for internal use within the class or module. 
        # This is a convention in Python to signal that these attributes or methods should not be accessed directly from outside the class, although it does not enforce any access restrictions.
        self._design_standard = self._access_design_standard()  # This attribute is intended for internal use and should not be accessed directly from outside the class.
        print(f'Wheel created with size: {self.size} and design standard: {self._design_standard}')

    # Prefix non-public methods with a single underscore to indicate that they are intended for internal use within the class or module.
    def _access_design_standard(self) -> str:
        return 'wheel_design_v1'  # This method is intended for internal use and should not be accessed directly from outside the class.
    
    # Double underscore prefix (name mangling) is used to make an attribute or method private to the class, meaning it cannot be accessed directly from outside the class.
    # Is single and double underscore prefix the same? No, they are not the same. 
    # A single underscore prefix is a convention to indicate that an attribute or method is intended for internal use, but it can still be accessed from outside the class. A double underscore prefix triggers name mangling, which makes the attribute or method private to the class and prevents direct access from outside the class. 
    # However, it can still be accessed using a special syntax (e.g., _ClassName__attribute) if needed.
    # A double underscore prefix is used to avoid name clashes in subclasses, as it changes the name of the attribute or method to include the class name, 
    # making it less likely to be accidentally overridden in a subclass.
    def __private_method(self) -> str:
        return 'This is a private method, not accessible from outside the class.'

class Car:

    def __init__(self, brand: str, wheel_size: int):
        self.brand = brand
        self.wheels = [Wheel(size=wheel_size) for _ in range(4)]  # A car has 4 wheels, composition of Wheel class

my_car = Car(brand='Toyota', wheel_size=16)
print(f'My car wheel size: {my_car.wheels[0].size}, wheel count: {len(my_car.wheels)}')
print('*'*20)

# Modules are files containing Python code that can define functions, classes, and variables. 
# Module is the python file without the .py extension.
# import statemtent is used to import a module into another module or script. 
# Using import * is not a best practice:
# - is generally discouraged as it can lead to namespace pollution and make it unclear which names are defined in the current namespace. It can also cause conflicts if different modules define the same name.
# - can bring unexpected objects into the current namespace, making it harder to understand where certain functions or variables are coming from.

from math import sqrt  # Importing the sqrt function from the math module
print(f'Square root of 16 is: {sqrt(16)}')
print('*'*20)

import this # Importing the this module, which contains the Zen of Python, a collection of guiding principles for writing Python code.
print('*'*20)

# Organizing modules into packages

# A package is a collection of modules organized in a directory hierarchy. 
# A package is a way to organize related modules together and it typically contains an empty __init__.py file to indicate that the directory is a package.
# Think of package as a namespace that contains multiple modules, and a module as a file that contains Python code (functions, classes, variables) that can be imported and used in other parts of the code.

# The __init__.py file cam be empty or it can contain importing of specific modules or functions which can be accessed directly when the package is imported. 
# For example, if __init__.py contains "from .math_utils import sqrt", then you can access the sqrt function directly by importing the package 
# (e.g., from utils import sqrt) without needing to specify the module (math_utils).

# src/
# main.py
# utils/
#      __init__.py
#     math_utils.py
#     string_utils.py

# Usage:
# from utils.math_utils import sqrt

# Relative imports example:
# from .math_utils import sqrt  # This would be used within a module in the same package to import the sqrt function from math_utils.py
# Zen of Python suggests that flattening code is better than nesting it, so it's generally recommended to avoid deep package hierarchies and keep the structure of your packages as simple as possible.

# What's use of global variables? (Use with caution)
# Global variables are variables that are defined outside of any function or class and can be accessed from anywhere in the module. 
# They can be useful for storing values that need to be shared across multiple functions or classes, but they should be used with caution as they can lead to code that is difficult to understand and maintain.

# Methods go in classes, classes go in modules, and modules go in packages.
# Classes can be defined anywhere also in a method! (But generally defined in a module)