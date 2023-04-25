from rclone_decrypt import __version__
from rclone_decrypt import decrypt

import filecmp
import pytest
import os
import shutil

decrypt_rclone_config_file = 'tests/rclone_decrypt.conf'
default_out_dir = 'out'
test_dir = 'tests'

@pytest.fixture()
def setup():
    """
    Remove all the decrypted files before each test
    """
    if os.path.isdir(default_out_dir):
        shutil.rmtree('out')

def test_version():
    assert __version__ == '0.1.0'


def compare_files(encrypted_folder :str):
    file_match_sub_folder = []
    for i in range(0,3):
        original_file = os.path.join(
                test_dir, 'raw_files', 'sub_folder', f'file{i}.txt')

        decrypted_file = os.path.join(
                default_out_dir, encrypted_folder,
                'sub_folder',
                f'file{i}.txt')

        file_match_sub_folder.append(filecmp.cmp(original_file, decrypted_file))

    original_file = os.path.join(test_dir, 'raw_files', 'file4.txt')
    decrypted_file = os.path.join( default_out_dir, encrypted_folder,
            'file4.txt')

    file_match = filecmp.cmp(original_file, decrypted_file)

    return all(file_match_sub_folder) and file_match


def decrypt_test(encrypted_folder :int, files :str) -> bool:
    instance = decrypt.get_rclone_instance(decrypt_rclone_config_file, files)

    decrypt.decrypt(instance,
                    files,
                    decrypt.default_output_folder)

    return compare_files(encrypted_folder)


def test_encrypted_file0(setup):
    """
    Test that encrypted files with unencrypted file names and folder names are
    decrypted
    """
    folder = 'encrypted_files0'
    files = f'tests/{folder}'
    assert(decrypt_test(folder, files) == True)


def test_encrypted_file1(setup):
    """
    Test that encrypted files with encrypted file names and unencrypted folder
    names are decrypted
    """
    folder = 'encrypted_files1'
    files = f'tests/{folder}'
    assert(decrypt_test(folder, files) == True)


def test_encrypted_file2(setup):
    """
    Test that encrypted files with encrypted file names and folder
    names are decrypted
    """
    encypted_folder = '0f12hh28evsof1kgflv67ldcngbgfa8j4viad0q5ie7mj1n1m490'
    decrypted_folder = 'encrypted_files2'
    files = f'tests/{encypted_folder}'
    assert(decrypt_test(decrypted_folder, files) == True)


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
    files = 'tests/something_fake'
    instance = decrypt.get_rclone_instance('', files)
    assert(instance is None)


def test_config_file():
    """
    Test behavior when provided valid config file
    """
    files = 'tests/something_fake'
    instance = decrypt.get_rclone_instance(decrypt_rclone_config_file, files)
    assert(instance is not None)
