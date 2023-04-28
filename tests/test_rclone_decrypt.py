from rclone_decrypt import __version__
from rclone_decrypt import decrypt

import filecmp
import pytest
import os
import shutil
import tempfile

decrypt_rclone_config_file = os.path.join("tests", "rclone_decrypt.conf")
test_dir = "tests"


def nuke_dir(dir_to_nuke):
    if os.path.isdir(dir_to_nuke):
        shutil.rmtree(dir_to_nuke)


@pytest.fixture()
def setup_and_teardown():
    """
    Remove all the decrypted files before each test
    """
    nuke_dir(decrypt.default_output_dir)
    yield
    nuke_dir(decrypt.default_output_dir)


def test_version():
    assert __version__ == "0.1.0"


def compare_files(decrypted_folder: str,
                  out_dir: str = decrypt.default_output_dir):
    file_match_sub_folder = []
    for i in range(0, 3):
        original_file = os.path.join(
            test_dir, "raw_files", "sub_folder", f"file{i}.txt"
        )

        decrypted_file = os.path.join(
            out_dir, decrypted_folder, "sub_folder", f"file{i}.txt"
        )

        file_match_sub_folder.append(
                filecmp.cmp(original_file, decrypted_file))

    original_file = os.path.join(test_dir, "raw_files", "file4.txt")
    decrypted_file = os.path.join(out_dir, decrypted_folder, "file4.txt")

    file_match = filecmp.cmp(original_file, decrypted_file)

    return all(file_match_sub_folder) and file_match


def decrypt_test(decrypted_folder: int, files: str) -> bool:
    decrypt.decrypt(
            files, decrypt_rclone_config_file, decrypt.default_output_dir)

    return compare_files(decrypted_folder)


def test_encrypted_file0(setup_and_teardown):
    """
    Test that encrypted files with unencrypted file names and folder names are
    decrypted
    """
    folder = "encrypted_files0"
    files = os.path.join("tests", folder)

    assert decrypt_test(folder, files) is True


def test_encrypted_file1(setup_and_teardown):
    """
    Test that encrypted files with encrypted file names and unencrypted folder
    names are decrypted
    """
    folder = "encrypted_files1"
    files = os.path.join("tests", folder)

    assert decrypt_test(folder, files) is True


def test_encrypted_file2(setup_and_teardown):
    """
    Test that encrypted files with encrypted file names and folder
    names are decrypted
    """
    encrypted_folder = "0f12hh28evsof1kgflv67ldcngbgfa8j4viad0q5ie7mj1n1m490"
    decrypted_folder = "encrypted_files2"
    files = os.path.join("tests", encrypted_folder)

    assert decrypt_test(decrypted_folder, files) is True


def test_decrypted_files_default_location(setup_and_teardown):
    """
    Test that decrypted files are placed into the default folder location
    """
    folder = "encrypted_files0"
    files = os.path.join("tests", folder)

    decrypt.decrypt(files, decrypt_rclone_config_file)

    files_match = compare_files(folder, decrypt.default_output_dir)

    assert files_match is True


def test_decrypted_files_defined_location():
    """
    Test that decrypted files are placed into a defined folder location
    """
    folder = "encrypted_files0"
    files = os.path.join("tests", folder)

    with tempfile.TemporaryDirectory() as defined_out_location:
        decrypt.decrypt(
                files, decrypt_rclone_config_file, defined_out_location
                )

        files_match = compare_files(folder, defined_out_location)
        assert files_match is True


def test_individual_file():
    """
    Test that individually specified files are decrypted
    """
    decrypted_file_name = "file2.txt"
    encrypted_file_name = f"{decrypted_file_name}.bin"

    encrypted_file_path = os.path.join(
        "tests", "encrypted_files0", "sub_folder", encrypted_file_name)

    with tempfile.TemporaryDirectory() as defined_out_location:
        decrypt.decrypt(
            encrypted_file_path, decrypt_rclone_config_file,
            defined_out_location)

        decrypted_file_path = os.path.join(
                defined_out_location, decrypted_file_name)

        unencrypted_original_file_path = os.path.join(
            test_dir, "raw_files", "sub_folder", f"{decrypted_file_name}")

        file_match = filecmp.cmp(
                unencrypted_original_file_path, decrypted_file_path)

        assert file_match is True


def test_no_config_file():
    """
    Test behavior when provided no config file
    """
    files = os.path.join("tests", "something_fake")
    instance = decrypt.get_rclone_instance("", files, "a_dir_name")

    assert instance is None


def test_config_file():
    """
    Test behavior when provided valid config file
    """
    files = os.path.join("tests", "something_fake")
    instance = decrypt.get_rclone_instance(
        decrypt_rclone_config_file, files, "a_dir_name"
    )

    assert instance is not None
