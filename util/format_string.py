def normalize_name(name):
    # Replace hyphens with spaces
    name = name.replace('-', ' ')
    # Convert to lowercase
    name = name.lower()
    # Create a translation table for Turkish letters
    turkish_map = str.maketrans({
        'ç': 'c',
        'ğ': 'g',
        'ı': 'i',
        'ö': 'o',
        'ş': 's',
        'ü': 'u',
        # In case accented variants show up
        'â': 'a',
        'î': 'i',
        'û': 'u'
    })
    # Translate and return the normalized name
    return name.translate(turkish_map)

def turkish_upper(text: str) -> str:
    # Create a translation table for Turkish-specific characters.
    translation = {
        ord('i'): 'İ',  # lowercase 'i' to uppercase 'İ'
        ord('ı'): 'I',  # lowercase 'ı' to uppercase 'I'
        ord('ğ'): 'Ğ',
        ord('ü'): 'Ü',
        ord('ş'): 'Ş',
        ord('ö'): 'Ö',
        ord('ç'): 'Ç',
    }

    # First, apply the Turkish-specific translations.
    text = text.translate(translation)

    # Then, apply the regular uppercase conversion.
    return text.upper()