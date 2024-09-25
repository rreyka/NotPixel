import random

def get(path):
    width = 40
    height = 20
    colors = [' ', '#', '.', '*']
    return [[random.choice(colors) for _ in range(width)] for _ in range(height)]
