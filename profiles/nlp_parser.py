import re

class NaturalLanguageParser:
    """Parses natural language queries into filter parameters"""
    
    # Keyword mappings
    GENDER_KEYWORDS = {
        'male': 'male', 'males': 'male', 'man': 'male', 'men': 'male',
        'boy': 'male', 'boys': 'male',
        'female': 'female', 'females': 'female', 'woman': 'female', 'women': 'female',
        'girl': 'female', 'girls': 'female',
    }
    
    AGE_GROUP_KEYWORDS = {
        'child': 'child', 'children': 'child', 'kid': 'child', 'kids': 'child',
        'teenager': 'teenager', 'teenagers': 'teenager', 'teen': 'teenager', 'teens': 'teenager',
        'adult': 'adult', 'adults': 'adult',
        'senior': 'senior', 'seniors': 'senior', 'elderly': 'senior', 'old': 'senior',
    }
    
    # Age range mappings (descriptive terms to numeric ranges)
    AGE_RANGES = {
        'young': (16, 24),
        'youth': (15, 25),
        'middle aged': (40, 60),
        'middle-aged': (40, 60),
    }
    
    # Country mappings (common names to ISO codes)
    COUNTRY_MAPPINGS = {
        'nigeria': 'NG', 'kenya': 'KE', 'south africa': 'ZA', 'ghana': 'GH',
        'egypt': 'EG', 'morocco': 'MA', 'angola': 'AO', 'ethiopia': 'ET',
        'tanzania': 'TZ', 'uganda': 'UG', 'cameroon': 'CM', 'senegal': 'SN',
        'zimbabwe': 'ZW', 'rwanda': 'RW', 'tunisia': 'TN', 'algeria': 'DZ',
        'sudan': 'SD', 'libya': 'LY', 'congo': 'CG', 'ivory coast': 'CI',
        "côte d'ivoire": 'CI',
    }
    
    @classmethod
    def parse(cls, query):
        """Parse natural language query and return filter parameters"""
        if not query or not query.strip():
            return None, "Unable to interpret query"
        
        query = query.lower().strip()
        filters = {}
        
        # Extract gender
        for word, gender in cls.GENDER_KEYWORDS.items():
            if word in query:
                filters['gender'] = gender
                break
        
        # Extract age group
        for word, age_group in cls.AGE_GROUP_KEYWORDS.items():
            if word in query:
                filters['age_group'] = age_group
                break
        
        # Extract country
        for country_name, iso_code in cls.COUNTRY_MAPPINGS.items():
            if country_name in query:
                filters['country_id'] = iso_code
                break
        
        # Extract descriptive age ranges
        for range_name, (min_age, max_age) in cls.AGE_RANGES.items():
            if range_name in query:
                filters['min_age'] = min_age
                filters['max_age'] = max_age
                break
        
        # Pattern: "above X" or "over X"
        above_match = re.search(r'above\s+(\d+)|over\s+(\d+)', query)
        if above_match:
            age = int(above_match.group(1) or above_match.group(2))
            filters['min_age'] = age
        
        # Pattern: "below X" or "under X"
        below_match = re.search(r'below\s+(\d+)|under\s+(\d+)', query)
        if below_match:
            age = int(below_match.group(1) or below_match.group(2))
            filters['max_age'] = age
        
        # Pattern: "between X and Y"
        between_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', query)
        if between_match:
            filters['min_age'] = int(between_match.group(1))
            filters['max_age'] = int(between_match.group(2))
        
        # Pattern: "age X" or "aged X"
        age_match = re.search(r'age\s+(\d+)|aged\s+(\d+)', query)
        if age_match:
            age = int(age_match.group(1) or age_match.group(2))
            filters['min_age'] = age
            filters['max_age'] = age
        
        # If no filters were identified, return error
        if not filters:
            return None, "Unable to interpret query"
        
        return filters, None