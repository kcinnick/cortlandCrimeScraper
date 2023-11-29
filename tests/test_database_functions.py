from database import remove_non_standard_characters


def test_remove_non_standard_characters():
    string_with_invalid_character = ('This is\n '
                                     'a string w�th an invalid character.')
    string_with_invalid_character_removed = remove_non_standard_characters(string_with_invalid_character)
    assert string_with_invalid_character_removed == 'This is a string wth an invalid character.'
