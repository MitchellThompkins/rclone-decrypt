import click
import logging
import os
import rclone
import tempfile

def print_error(msg):
    print(f'ERROR: {msg}')

def get_rclone_instance(config:str):
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

    return rclone_instance


def decrypt(rclone_instance, files):
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
            out = rclone_instance.copy(f'{r}{tmp_dir}', 'tmp_out/')

        os.rename(tempfile_full_path, file_full_path)


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
            instance = get_rclone_instance(config)
            decrypt(instance, files)

    except ValueError as err:
        print_error(err)

if __name__ == '__main__':
    cli()
