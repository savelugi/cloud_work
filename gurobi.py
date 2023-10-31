import gurobipy as grb

class Gurobi:
    def __init__(self):
        self.model = grb.Model()