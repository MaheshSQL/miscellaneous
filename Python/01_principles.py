# Requires Python 3.13

# SOLID
# 1. Single Responsibility Principle: A class should have a single responsibility and should not have more than one reason to change.
# 2. Open/Closed Principle: Classes are open for extension but closed for modification.
# 3. Liskov Substitution Principle: Subclasses must be substitutable for their base classes.
# 4. Interface Segregation Principle: Keep the interface as small as possible. 
# 5. Dependency Inversion Principle: Depend on abstractions, not on concrete implementations. e.g. Vehicle instead of Car, Bike, etc.


# Interface Segregation Principle
# A class should not be forced to implement interfaces it does not use.
from abc import ABC, abstractmethod

# Why subclassing from ABC?
# The ABC (Abstract Base Class) module provides a way to define abstract base classes in Python. By subclassing from ABC, we can create abstract classes that cannot be instantiated directly and can contain abstract methods that must be implemented by any concrete subclass. This helps to enforce a contract for subclasses, ensuring that they implement the required methods and adhere to the intended design of the class hierarchy.
# Is it possible to impement an interface without subclassing from ABC?
# Yes, in Python, you can define an interface using a regular class with method definitions that raise NotImplementedError. This approach does not require subclassing from ABC, but it lacks some of the formal enforcement provided by ABCs.
# With ABC you get "TypeError: Can't instantiate abstract class Square without an implementation for abstract method 'calculate_area'" as soon as you try to create an instance of Square without implementing the calculate_area method. 
class Shape(ABC):
    @abstractmethod
    def calculate_area(self) -> float:
        pass

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def calculate_area(self) -> float:
        return 3.14 * self.radius ** 2
    
class Square(Shape):
    def __init__(self, side_length: float):
        self.side_length = side_length

    def calculate_area(self) -> float:
        return self.side_length ** 2
    
# Example usage
circle = Circle(radius=5)
print(f'Area of the circle: {circle.calculate_area()}')

square = Square(side_length=4)
print(f'Area of the square: {square.calculate_area()}')
print('*'*20)

# Open/Closed Principle

class Vehicle(ABC):
    @abstractmethod
    def start_engine(self) -> None:
        pass

class Car(Vehicle):
    def start_engine(self) -> None:
        print("Car engine started.")

class MotorBike(Vehicle):
    def start_engine(self) -> None:
        print("Motorbike engine started.")

car = Car()
car.start_engine()

motorbike = MotorBike()
motorbike.start_engine()
print('*'*20)

# Liskov Substitution Principle
# If we have a base class Bird, we want all of the subclasses, Sparrow, Penguin, and anything else we might need to invent, to have the same interface as the base class. They’re all birds, each with unique implementation details. By having the same interface, any of the subclasses can be used in place of the base class.

class Bird(ABC):
    @abstractmethod
    def fly(self) -> None:
        pass

class Sparrow(Bird):
    def fly(self) -> None:
        print("Sparrow is flying.")

class Penguin(Bird):
    def fly(self) -> None:
        raise NotImplementedError("Penguins cannot fly.")
    
sparrow = Sparrow()
sparrow.fly()
penguin = Penguin()
try:
    penguin.fly()
except NotImplementedError as e:
    print(e)
print('*'*20)

# Dependency Inversion Principle

class Database(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

class MySQLDatabase(Database):
    def connect(self) -> bool:
        print("Connected to MySQL Database")
        return True
    
class PostgreSQLDatabase(Database):
    def connect(self) -> bool:
        print("Connected to PostgreSQL Database")
        return True
    
class Application:
    def __init__(self, database: Database): # See how we depend on the abstraction (Database) rather than the concrete implementation (MySQLDatabase or PostgreSQLDatabase)
        self.database = database

    def run(self) -> None:
        if self.database.connect():
            print("Application is running with the database connection.")
        else:
            print("Failed to connect to the database.")

mysql = MySQLDatabase()
app = Application(mysql)
app.run()
print('*'*20)

# Single Responsibility Principle
# A class should have only one reason to change, meaning it should have only one responsibility

class AirConditioner:
    def __init__(self, brand: str):
        self.brand = brand

    def turn_on(self) -> None:
        print(f"{self.brand} Air Conditioner is turned on.")

class RemoteControl:
    def __init__(self, air_conditioner: AirConditioner):
        self.air_conditioner = air_conditioner

    def turn_on_ac(self) -> None:
        self.air_conditioner.turn_on()

ac = AirConditioner(brand="LG")
remote = RemoteControl(air_conditioner=ac)
remote.turn_on_ac()
print('*'*20)