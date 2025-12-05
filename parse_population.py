import json
import re

def parse_population(file_path):
    population_data = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 8:
            continue
            
        name = parts[1]
        if not name:
            continue
            
        # Remove reference markers like [16]
        name = re.sub(r'\[\d+\]', '', name).strip()
        
        pop1_str = parts[6]
        pop2_str = parts[7]
        
        population = None
        
        # Try Pop1
        if pop1_str and pop1_str != '?':
            try:
                population = int(pop1_str.replace(',', ''))
            except ValueError:
                pass
                
        # If Pop1 failed or empty, try Pop2
        if population is None and pop2_str and pop2_str != '?':
            try:
                population = int(pop2_str.replace(',', ''))
            except ValueError:
                pass
        
        if population is not None:
            population_data[name] = population
            
    return population_data

if __name__ == "__main__":
    data = parse_population('wikipedia_snippet.txt')
    print(json.dumps(data, indent=4, sort_keys=True))
