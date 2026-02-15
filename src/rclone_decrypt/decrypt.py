import logging
import os
import re
import sys
import shutil
import tempfile
import subprocess

from statemachine import State, StateMachine

logger = logging.getLogger("rclone_decrypt")

default_output_dir = os.path.join(
    os.path.expanduser("~"), "Downloads", "rclone-decrypted"
)

try:
    if shutil.which("rclone"):
        # Get the rclone config file path dynamically
        cmd = ["rclone", "config", "file"]
        out = subprocess.check_output(cmd).decode().strip()
        # The output format is usually:
        # "Configuration file is stored at:\n/path/to/rclone.conf"
        # We need to parse the last line
        default_rclone_conf_dir = out.splitlines()[-1]
    else:
        raise FileNotFoundError("rclone executable not found")
except (subprocess.CalledProcessError, FileNotFoundError):
    # Fallback to the previous default if rclone command fails or is not found
    default_rclone_conf_dir = os.path.join(
        os.environ["HOME"], ".config", "rclone", "rclone.conf"
    )

if sys.platform == "win32":
    # Windows default: %APPDATA%/rclone/rclone.conf
    default_rclone_conf_dir = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "rclone",
        "rclone.conf",
    )
else:
    # macOS/Linux default: ~/.config/rclone/rclone.conf
    default_rclone_conf_dir = os.path.join(
        os.path.expanduser("~"), ".config", "rclone", "rclone.conf"
    )


class ConfigFileError(Exception):
    def __init__(self, *args, **kwargs):
        default_message = """There is a problem with the rclone
        configuration file"""

        if not args:
            args = (default_message,)

        # Call super constructor
        super().__init__(*args, **kwargs)


class RCloneExecutableError(Exception):
    def __init__(self, *args, **kwargs):
        default_message = """rclone executable not found. Please install
        rclone and ensure it is in your PATH."""

        if not args:
            args = (default_message,)

        # Call super constructor
        super().__init__(*args, **kwargs)


def print_error(msg: str) -> None:
    """
    Print generic error.
    """
    logger.error(f"{msg}")


class ConfigWriterControl(StateMachine):
    searching_for_start = State(initial=True)
    type_check = State()
    writing = State()
    completed = State(final=True)

    search = searching_for_start.to(searching_for_start)
    validate = searching_for_start.to(type_check)
    is_valid = type_check.to(writing)
    is_invalid = type_check.to(searching_for_start)
    write = type_check.to(writing) | writing.to(writing)
    write_complete = writing.to(searching_for_start)
    complete = searching_for_start.to(completed) | writing.to(completed)

    def __init__(self, cfg_file: str) -> None:
        self.cfg_file = cfg_file
        self.cached_entry_start = None

        super(ConfigWriterControl, self).__init__()

    def before_validate(self, line: str) -> None:
        self.cached_entry_start = line

    def before_write(self, line: str) -> None:
        self.cfg_file.write(line)

    def before_is_valid(self, line: str) -> None:
        self.cfg_file.write(self.cached_entry_start)
        self.cfg_file.write(line)


def get_rclone_config_path(
    config: str, files: str, remote_folder_name: str
) -> str:
    """
    Opens a config file and strips out all of the non-crypt type entries,
    modifies the remote to be local directory.

    Returns the path to the temporary rclone config file.
    """
    config_path = None

    try:
        with open(config, "r") as f:
            config_file = f.readlines()

            # Create a temporary file that persists until manually deleted or
            # cleaned up by caller.
            # We use delete=False so we can return the path and use it later.
            # It will be created in the system temp dir or temp_dir_name if
            # passed? Actually, let's create it inside remote_folder_name
            # (which is a temp dir).

            config_path = os.path.join(remote_folder_name, "rclone.conf")

            with open(config_path, "w") as config_out:
                config_state = ConfigWriterControl(config_out)

                for line in config_file:
                    state_id = config_state.current_state.id

                    if state_id == "searching_for_start":
                        start_of_entry = re.search("\\[.*?\\]", line)

                        if start_of_entry is not None:
                            config_state.validate(line)
                        else:
                            config_state.search()

                    elif state_id == "type_check":
                        regex_str = "type\\s*=\\s*([\\S\\s]+)"
                        entry_type = re.search(regex_str, line)
                        if entry_type is not None:
                            entry_type = entry_type.group(1).strip()
                            if entry_type == "crypt":
                                valid_str = f"type = {entry_type}\n"
                                config_state.is_valid(valid_str)
                            else:
                                config_state.is_invalid()

                    elif state_id == "writing":
                        regex_str = "remote\\s*=\\s*([\\S\\s]+)"
                        remote = re.search(regex_str, line)
                        if remote is not None:
                            config_state.write(
                                f"remote =\
                                    {remote_folder_name}/\n"
                            )

                        elif line == "\n":
                            config_state.write(line)
                            config_state.write_complete()

                        else:
                            config_state.write(line)

                config_state.complete()

    except FileNotFoundError as err:
        print_error(err)
        return None

    return config_path


def rclone_copy(config_path: str, output_dir: str) -> None:
    """
    Calls the rclone copy function via a shell instance and places the
    decrypted files into the output_dir
    """
    # convert list of remotes in str format into a list
    list_cmd = ["rclone", "--config", config_path, "listremotes"]
    try:
        out = subprocess.check_output(list_cmd).decode()
        remotes = out.splitlines()
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to list remotes: {e}")
        return

    for r in remotes:
        print(f"Copying and decrypting: {r}")
        copy_cmd = [
            "rclone",
            "--config",
            config_path,
            "copy",
            f"{r}",
            f"{output_dir}",
        ]
        # TODO(@mitchellthompkins): check return code for success
        subprocess.run(copy_cmd, check=True)


def decrypt(
    files: str,
    config: str = default_rclone_conf_dir,
    output_dir: str = default_output_dir,
) -> None:
    """
    Sets up the files or directories to be decrypted by moving them to the
    correct relative path. The appropriate temporary config file is generated
    and the appropriate rclone_copy function is then called to perform the
    decryption.

    Explicitly, this creates a temporary directory at the same root as where
    this is called from, moves the files (or file) to be decrypted to that
    directory, modifies a temporary config file in order to point rclone to a
    folder in _this_ directory, calls `rclone --config config file copy
    remote:local_tmp_dir out` and then moves the files back to their original
    location.
    """
    if shutil.which("rclone") is None:
        raise RCloneExecutableError()

    actual_path = os.path.abspath(files)

    try:
        # Create temp dir in the same directory as the target file/folder to
        # ensure fast, atomic moves (os.rename) where possible, and avoid
        # cross-device issues.
        with tempfile.TemporaryDirectory(
            dir=os.path.dirname(actual_path)
        ) as temp_dir_name:
            # Ensure path uses forward slashes for rclone config
            # compatibility on Windows
            # Although update branch didn't have this, it's safer to keep it
            # if we are creating paths for rclone.
            # But get_rclone_config_path writes the config file now,
            # and it writes {remote_folder_name}/ which is the temp dir.
            # So normalization might be good.
            # However, HEAD passed normalized_temp_dir to get_rclone_instance.
            # update branch passed temp_dir_name directly.
            # I will pass temp_dir_name directly to be safe with update logic,
            # or normalized if I think it helps. HEAD thought it helped.
            # I'll stick to temp_dir_name to minimize risk of path mismatch,
            # unless I see a reason.
            # Actually, HEAD comment says "compatibility on Windows".
            # I'll add the normalization back if I see it's used in config writing.
            # In update logic: config_state.write(f"remote = {remote_folder_name}/\n")
            # If remote_folder_name has backslashes, rclone config might barf?
            # Rclone usually handles both, but forward slashes are safer.
            # I will normalize it.
            normalized_temp_dir = temp_dir_name.replace(os.sep, "/")

            config_path = get_rclone_config_path(
                config, files, normalized_temp_dir
            )

            if config_path is None:
                raise ConfigFileError("config_path cannot be None")

            if output_dir is default_output_dir:
                # If no output_dir is provided, put the de-crypted file into a
                # folder called 'out' that lives in the current working
                # directory
                output_dir = os.path.abspath(default_output_dir)
                logger.info(
                    "No output directory specified. "
                    f"Defaulting to: {output_dir}"
                )

            # if the output folder doesn't exist, make it
            if not os.path.isdir(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)

            dir_or_file_name = os.path.basename(actual_path)
            temp_file_path = os.path.join(temp_dir_name, dir_or_file_name)

            # Move the folder
            logger.info(f"Decrypting: {actual_path}")
            shutil.move(actual_path, temp_file_path)

            try:
                # Do the copy, we wrap this in a try in case the user
                # interrupts the process, otherwise the file won't be
                # moved back
                rclone_copy(config_path, output_dir)
                logger.info(
                    f"Decryption complete. Files saved to: {output_dir}"
                )
            except KeyboardInterrupt:
                logger.info("\n\tterminated rclone copy!")
                print("\n\tterminated rclone copy!")

            finally:
                # Move it back
                shutil.move(temp_file_path, actual_path)

    except ConfigFileError as err:
        print_error(err)
