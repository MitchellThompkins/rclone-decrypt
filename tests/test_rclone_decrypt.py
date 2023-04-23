from rclone_decrypt import __version__
from rclone_decrypt import decrypt

def test_version():
    assert __version__ == '0.1.0'

def test_encrypted_file0():
    """
    Test that encrypted files with unencrypted file names and folder names are
    decrypted
    """
    pass

def test_encrypted_file1():
    """
    Test that encrypted files with encrypted file names and unencrypted folder
    names are decrypted
    """
    pass

def test_encrypted_file2():
    """
    Test that encrypted files with encrypted file names and folder
    names are decrypted
    """
    pass

def test_decrypted_files_default_location():
    """
    Test that decrypted files are placed into the default folder location
    """
    pass

def test_decrypted_files_defined_location():
    """
    Test that decrypted files are placed into a defined folder location
    """
    pass

def test_individual_file():
    """
    Test that individually specified files are decrypted
    """
    pass

def test_no_config_file():
    """
    Test behavior when provided no config file
    """
    instance = decrypt.get_rclone_instance('')
    assert(instance is None)

def test_config_file():
    """
    Test behavior when provided valid config file
    """
    instance = decrypt.get_rclone_instance('tests/rclone_decrypt.conf')
    assert(instance is not None)
