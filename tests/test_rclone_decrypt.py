from rclone_decrypt import __version__
from rclone_decrypt import decrypt

import filecmp
import pytest
import os
import shutil

decrypt_rclone_config_file = 'tests/rclone_decrypt.conf'
default_out_dir = 'out'
test_dir = 'tests'

def nuke_dir(dir_to_nuke):
    if os.path.isdir(dir_to_nuke):
        shutil.rmtree(dir_to_nuke)


@pytest.fixture()
def setup():
    """
    Remove all the decrypted files before each test
    """
    nuke_dir(default_out_dir)

def test_version():
    assert __version__ == '0.1.0'


def compare_files(decrypted_folder :str, out_dir:str =default_out_dir ):
    file_match_sub_folder = []
    for i in range(0,3):
        original_file = os.path.join(
                test_dir, 'raw_files', 'sub_folder', f'file{i}.txt')

        decrypted_file = os.path.join(
                out_dir, decrypted_folder,
                'sub_folder',
                f'file{i}.txt')

        file_match_sub_folder.append(filecmp.cmp(original_file, decrypted_file))

    original_file = os.path.join(test_dir, 'raw_files', 'file4.txt')
    decrypted_file = os.path.join( out_dir, decrypted_folder,
            'file4.txt')

    file_match = filecmp.cmp(original_file, decrypted_file)

    return all(file_match_sub_folder) and file_match


def decrypt_test(decrypted_folder :int, files :str) -> bool:
    decrypt.decrypt(decrypt_rclone_config_file,
                    files,
                    decrypt.default_output_folder)

    return compare_files(decrypted_folder)


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
    encrypted_folder = '0f12hh28evsof1kgflv67ldcngbgfa8j4viad0q5ie7mj1n1m490'
    decrypted_folder = 'encrypted_files2'
    files = f'tests/{encrypted_folder}'

    assert(decrypt_test(decrypted_folder, files) == True)


def test_decrypted_files_default_location():
    """
    Test that decrypted files are placed into the default folder location
    """
    folder = 'encrypted_files0'
    files = f'tests/{folder}'

    decrypt.decrypt(decrypt_rclone_config_file, files)

    files_match = compare_files(folder, decrypt.default_output_folder)

    assert(files_match == True)
    nuke_dir(decrypt.default_output_folder)


def test_decrypted_files_defined_location():
    """
    Test that decrypted files are placed into a defined folder location
    """
    folder = 'encrypted_files0'
    files = f'tests/{folder}'
    defined_out_location = '/tmp/i_am_a_directory'

    decrypt.decrypt(decrypt_rclone_config_file,
                    files,
                    defined_out_location)

    files_match = compare_files(folder, defined_out_location)
    assert(files_match == True)
    nuke_dir(defined_out_location)


def test_individual_file():
    """
    Test that individually specified files are decrypted
    """
    decrypted_file_name = 'file2.txt'
    encrypted_file_name = f'{decrypted_file_name}.bin'

    encrypted_file_path = f'tests/encrypted_files0/sub_folder/{encrypted_file_name}'

    defined_out_location = '/tmp/i_am_also_a_directory'

    decrypt.decrypt(decrypt_rclone_config_file,
                    encrypted_file_path,
                    defined_out_location)

    decrypted_file_path = f'{defined_out_location}/{decrypted_file_name}'

    unencrypted_original_file_path = os.path.join( test_dir, 'raw_files', 'sub_folder',
            f'{decrypted_file_name}')

    file_match = filecmp.cmp(unencrypted_original_file_path, decrypted_file_path)
    assert(file_match == True)

    nuke_dir(defined_out_location)


def test_no_config_file():
    """
    Test behavior when provided no config file
    """
    files = 'tests/something_fake'
    instance = decrypt.get_rclone_instance('', files, 'a_dir_name')

    assert(instance is None)


def test_config_file():
    """
    Test behavior when provided valid config file
    """
    files = 'tests/something_fake'
    instance = decrypt.get_rclone_instance(decrypt_rclone_config_file, files,
            'a_dir_name')

    assert(instance is not None)
