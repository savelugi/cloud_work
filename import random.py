import random

# Seed-del inicializált véletlenszám-generátor
seeded_random = random.Random(42)

# Seed nélküli, alapértelmezett véletlenszám-generátor
default_random = random.Random()

choices = ['alma', 'banán', 'cseresznye']

# Seed-del inicializált véletlenszám-generátor használata
print("Seed-del:")
print(seeded_random.choice(choices))  # Mindig ugyanazt az elemet fogja visszaadni
print(seeded_random.choice(choices))  # Mindig ugyanazt az elemet fogja visszaadni
print(seeded_random.choice(choices))  # Mindig ugyanazt az elemet fogja visszaadni

# Seed nélküli véletlenszám-generátor használata
print("Seed nélkül:")
print(default_random.choice(choices))  # Véletlenszerű elem
print(default_random.choice(choices))  # Véletlenszerű elem
print(default_random.choice(choices))  # Véletlenszerű elem
