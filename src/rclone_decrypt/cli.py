import click
import logging
import os
import rclone
import tempfile

def print_error(msg):
    print(f'ERROR: {msg}')

def decrypt(config:str, files):
    #TODO: Handle if path or file name
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
                            config.write('remote = .\n')
                        else:
                            config.write(line)

                # Open the modified temporary file and create our instance fromt
                # hat
                with open(tmp_config_file.name, 'r') as t:
                    o = t.read()
                    rclone_instance = rclone.with_config(o)

        if rclone_instance is None:
            raise ConfigFileError("The rclone instance was not created.")

    except ValueError as err:
        print_error(err)

    # Put this file to be de-crypted into a tmp directory. This is b/c I've had
    # trouble de-crypting single files with rclone. It's happy to de-crypt all
    # the files in a directory, so when working with a single file, I just move
    # it to a directory and point rclone to that
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as tmpdirname:
        file_full_path = os.path.abspath(files)

        file_name = os.path.basename(files)
        tempfile_full_path = os.path.join(tmpdirname, file_name)

        os.rename(file_full_path, tempfile_full_path)

        tmp_dir = os.path.basename(os.path.dirname(tempfile_full_path))

        #convert list of remotes in str format into a list
        remotes = rclone_instance.listremotes()['out'].decode().splitlines()

        for r in remotes:
            print(f'{r}{tmp_dir}')
            out = rclone_instance.copy(f'{r}{tmp_dir}', 'tmp_out/')
            #out = rclone_instance.copy(f'{r}tmp', 'tmp_out/')

        os.rename(tempfile_full_path, file_full_path)

# rclone --config rclone_tmp.conf -vv copy encrypted_b2:tmp2/ tmp_out/mthompkins_backed_up_

# If file ends in .bin, then it's not encrypted, Othwerise assume encrypted and
# try to find where valid filename starts. This is the difference in starndard
# and "off" filename encryption

# rclone --config rclone_tmp.conf copy encrypted_b2:tmp/ tmp_out/


@click.command()
@click.option('--config',
        help='config file',
        required=True)
@click.option('--files',
        help='dir to de-crypt',
        default=None)
@click.option('--download',
        help='file or dir to download and de-crypt',
        default=None)
def cli(config, files, download):
    try:
        if files is None and download is None:
            raise ValueError("files and download cannot be None")
        else:
            decrypt(config, files)

    except ValueError as err:
        print_error(err)

if __name__ == '__main__':
    cli()
