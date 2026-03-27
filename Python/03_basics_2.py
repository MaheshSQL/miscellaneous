import abc

# Inheritance ('is-a')

class Employee(abc.ABC):

    def __init__(self, id: int, name: str, employee_type: str):
        self.id = id
        self.name = name
        self.employee_type = employee_type

    def display_employee_info(self):
        print(f'Employee ID:{self.id}\nEmployee Name:{self.name}\nEmployee Type:{self.employee_type}')

    @abc.abstractmethod
    def calculate_pay(self):
        pass


class FullTimeEmployee(Employee):

    def __init__(self, id: int, name: str, employee_type: str, base_salary: float):
        self.base_salary = base_salary
        super().__init__(id=id, name=name, employee_type=employee_type)

    def calculate_pay(self, bonus_perc: float):
        monthly_pay = self.base_salary/12 
        print(f'Total Pay (Full month): ${round(monthly_pay + (monthly_pay*bonus_perc),2)} (includes {round(bonus_perc*100,2)}% bonus)')

class Contractor(Employee):

    def __init__(self, id: int, name: str, employee_type: str, hourly_rate: float):
        self.hourly_rate = hourly_rate
        super().__init__(id=id, name=name, employee_type=employee_type)

    def calculate_pay(self, hours_worked: float):
        monthly_pay = self.hourly_rate*hours_worked
        print(f'Total Pay ({hours_worked} hours): ${round(monthly_pay,2)}')

print('*Inheritance*')
# emp = Employee(1, 'John Doe', 5000) # Will receive: TypeError: Can't instantiate abstract class Employee without an implementation for abstract method 'calculate_pay'
fte = FullTimeEmployee(1, 'John Doe', 'Full Time', 5000)
fte.display_employee_info()
fte.calculate_pay(bonus_perc=0.1)
print('*'*20)

contr = Contractor(2, 'Don Smith', 'Contractor', 3)
contr.display_employee_info()
contr.calculate_pay(hours_worked=160)
print('*'*20)

# Composition ('has-a')

class Component(abc.ABC):

    def __init__(self, brand: str):
        self.brand = brand

class CPU(Component):

    def __init__(self, brand: str, frequency_ghz: float):
        self.frequency_ghz = frequency_ghz
        super().__init__(brand)

    def process_data(self):
        print(f'Data processing started @{round(self.frequency_ghz,2)} GHz')

class RAM(Component):

    def __init__(self, brand: str, capacity_mb: int):
        self.capacity_mb = capacity_mb
        super().__init__(brand)

    def load_memory(self):
        print(f'Loaded memory with {round(self.capacity_mb/1024)} GB capacity')

class Computer():    

    def __init__(self, cpu_brand: str, cpu_frequency_ghz: float, ram_brand: str, ram_capacity_mb: int):
        self.cpu = CPU(brand=cpu_brand, frequency_ghz=cpu_frequency_ghz)
        self.ram = RAM(brand=ram_brand, capacity_mb=ram_capacity_mb)
        self.state = 'off'
        print(f'Computer initialised (state:{self.state})')

    def start(self):
        self.cpu.process_data()
        self.ram.load_memory()
        self.state = 'on'
        print(f'Computer started (state:{self.state})')

print('*Composition*')
pc = Computer(cpu_brand='intel', cpu_frequency_ghz=4.5, ram_brand='corsair', ram_capacity_mb=8192)
pc.start()
print('*'*20)

# Polymorphism ('Behaves differently based on implementation')

class PaymentMethod(abc.ABC):

    def __init__(self, payment_method_name: str):
        self.payment_method_name = payment_method_name
        print(f'Chosen payment method:{payment_method_name}')

    @abc.abstractmethod
    def pay(self):
        pass

class CreditCard(PaymentMethod):

    def __init__(self, payment_method_name: str, encrypted_cc_number: int, cc_user_name: str):
        self.encrypted_cc_number = encrypted_cc_number
        self.cc_user_name = cc_user_name
        super().__init__(payment_method_name)

    def pay(self, receiver: str, amount: float):
        print(f'Credit card details decrypted for encrypted card {self.encrypted_cc_number}')
        print(f'Payment of ${amount} sent to receiver {receiver}.')

class PayMate(PaymentMethod):

    def __init__(self, payment_method_name: str, user_name: str, auth_token: str):        
        self.user_name = user_name
        self.auth_token = auth_token
        super().__init__(payment_method_name)

    def pay(self, receiver: str, amount: float):
        print(f'User authentication completed using auth_token: {self.auth_token}')
        print(f'Payment of ${amount} sent to receiver {receiver}.')

print('*Polymorphism*')

cred_card = CreditCard(payment_method_name='Credit card', encrypted_cc_number='XXXXX', cc_user_name='Jo Blogs')
cred_card.pay(receiver='Jupyter Bikes', amount=75)
print()
pay_mate = PayMate(payment_method_name='PayMate', user_name='Sam L', auth_token='XXXXX')
pay_mate.pay(receiver='Hardware Warehouse', amount=94.99)

print('*'*20)