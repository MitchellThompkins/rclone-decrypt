import logging
import os
import rclone
import tempfile
import shutil
import sys

temporary_dir = 'temp_dir'
default_output_folder = 'out'

class ConfigFileError(Exception):
    def __init__(self, *args, **kwargs):
        default_message = """There is a problem with the rclone
        configuration file"""

        # if no arguments are passed set the first positional argument
        # to be the default message. To do that, we have to replace the
        # 'args' tuple with another one, that will only contain the message.
        # (we cannot do an assignment since tuples are immutable)
        # If you inherit from the exception that takes message as a keyword
        # maybe you will need to check kwargs here
        if not args: args = (default_message,)

        # Call super constructor
        super().__init__(*args, **kwargs)

def print_error(msg):
    print(f'ERROR: {msg}')


def get_rclone_instance(config:str, files:str, remote_folder_name:str):
    """
    """
    rclone_instance = None

    try:
        with open(config, 'r') as f:
            config_file = f.readlines()

            with tempfile.NamedTemporaryFile(mode='wt', delete=True) as tmp_config_file:
                # Open the config file and copy contents to a temporary file,
                with open(tmp_config_file.name, 'w') as config:
                    # For an entry marked as remote, replace it with '.' so that
                    # we manipulate a local file
                    for line in config_file:
                        if len(line.split('remote = ',1)) == 2:
                            config.write(f'remote = {remote_folder_name}/\n')
                        else:
                            config.write(line)

                # Open the modified temporary file and create our instance from
                # that
                with open(tmp_config_file.name, 'r') as t:
                    o = t.read()
                    rclone_instance = rclone.with_config(o)

        # I think that given a file, any file, rclone.with_config() will always
        # return _something_ as it doesn't validate the config file
        if rclone_instance is None:
            raise ConfigFileError("The rclone instance was not created.")

    except FileNotFoundError as err:
        print_error(err)

    return rclone_instance


def rclone_copy(rclone_instance, output_dir):
    # convert list of remotes in str format into a list
    remotes = rclone_instance.listremotes()['out'].decode().splitlines()

    # try to de-crypt for every type of remote until success
    for r in remotes:
        success = rclone_instance.copy(f'{r}', f'{output_dir}')
        if success == 0:
            break

def decrypt(config:str, files:str, output_dir=default_output_folder):
    """
    """
    try:
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir_name:
            rclone_instance = get_rclone_instance(config, files, temp_dir_name)

            if rclone_instance is None:
                raise ConfigFileError('rclone_instance cannot be None')


            if output_dir is default_output_folder:
                # If no output_dir is provided, put the de-crypted file into a
                # folder called 'out' that lives at the same base dir as that of the
                # input file
                base_file_dir = os.path.basename(os.path.dirname(files))
                file_input_dir = os.path.dirname(os.path.abspath(base_file_dir))
                output_dir = os.path.join(file_input_dir, output_dir)

            # if the output folder doesn't exist, make it
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)

            if os.path.isdir(files):
                # When folder names are encrypted, I don't think that the config
                # file can look wherever it wants in a sub directory, so the folder
                # we're looking for must live in the same root directory as where
                # rclone is called from
                    actual_path = os.path.abspath(files)
                    dir_name = os.path.basename(actual_path)
                    temp_file_path = os.path.join(os.getcwd(), temp_dir_name, dir_name)

                    # Move the folder
                    os.rename(actual_path, temp_file_path)

                    # Do the copy
                    rclone_copy(rclone_instance, output_dir)

                    # Move it back
                    os.rename(temp_file_path, actual_path)

            else:
                pass
                # Put this file to be de-crypted into a tmp directory. This is b/c
                # I've had trouble de-crypting single files with rclone. It's happy
                # to de-crypt all the files in a directory, so when working with a
                # single file, I just move it to a directory and point rclone to
                # that
                #with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir_name:
                #    actual_path = os.path.abspath(files)
                #    file_name = os.path.basename(actual_path)
                #    tempfile_full_path = os.path.join(temp_dir_name, file_name)

                #    os.rename(file_full_path, tempfile_full_path)

                #    tmp_dir = os.path.basename(os.path.dirname(tempfile_full_path))

                #    rclone_copy(rclone_instance, output_dir)

                #    os.rename(tempfile_full_path, file_full_path)

                #    # here
                #    actual_path = os.path.abspath(files)
                #    dir_name = os.path.basename(actual_path)
                #    temp_file_path = os.path.join(temp_dir_name, file_name)

                #    # Move the folder
                #    os.rename(actual_path, temp_file_path)

                #    # Do the copy
                #    rclone_copy(rclone_instance, output_dir)

                #    # Move it back
                #    os.rename(temp_file_path, actual_path)

    except ConfigFileError as err:
        print_error(err)
