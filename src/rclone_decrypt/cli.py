import click
import rclone

def print_error(msg):
    print(f'ERROR: {msg}')

def decrypt(files):
    pass

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
