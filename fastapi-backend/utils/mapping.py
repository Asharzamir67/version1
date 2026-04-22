# utils/mapping.py

def map_car_model(input_str: str) -> str:
    """
    Maps an input model string to a specific folder name.
    
    Logic:
    - Starts with "zre" (case-insensitive) -> corolla
    - Starts with "nsp" (case-insensitive) -> yaris
    - Otherwise -> other
    """
    from config import CAR_PREFIX_MAP, STATUS_OTHER
    
    if not input_str:
        return STATUS_OTHER
        
    m = input_str.lower()
    
    for prefix, folder in CAR_PREFIX_MAP.items():
        if m.startswith(prefix.lower()):
            return folder
            
    return STATUS_OTHER
