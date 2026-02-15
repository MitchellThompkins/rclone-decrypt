import logging
import os
import io
import re
import sys
import shutil
import tempfile

import rclone
from statemachine import State, StateMachine

logger = logging.getLogger("rclone_decrypt")

default_output_dir = os.path.join(
    os.path.expanduser("~"), "Downloads", "rclone-decrypted"
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


class SafeRClone(rclone.RClone):
    """
    A subclass of rclone.RClone that uses delete=False for the temporary
    config file. This prevents file locking issues on Windows where the file
    cannot be opened by the subprocess while it is still open in Python.
    """

    def run_cmd(self, command, extra_args=None):
        if extra_args is None:
            extra_args = []

        # Create a named temporary file, but don't delete it automatically
        # on close, so we can close it before passing to rclone.
        with tempfile.NamedTemporaryFile(mode="wt", delete=False) as cfg_file:
            cfg_file_path = cfg_file.name
            try:
                self.log.debug("rclone config: ~%s~", self.cfg)
                cfg_file.write(self.cfg)
                cfg_file.flush()
                # Close the file so other processes can access it (Windows fix)
                cfg_file.close()

                command_with_args = [
                    "rclone",
                    command,
                    "--config",
                    cfg_file_path,
                ]
                command_with_args += extra_args
                command_result = self._execute(command_with_args)
                return command_result
            finally:
                # Manually clean up the file
                if os.path.exists(cfg_file_path):
                    os.remove(cfg_file_path)


def get_rclone_instance(
    config: str, files: str, remote_folder_name: str
) -> rclone.RClone:
    """
    Opens a config file and strips out all of the non-crypt type entries,
    modifies the remote to be local directory.

    Returns an rclone instance.
    """
    rclone_instance = None

    try:
        with open(config, "r") as f:
            config_file = f.readlines()

            with io.StringIO() as tmp_config_file:
                config_state = ConfigWriterControl(tmp_config_file)

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

                # Get the content
                o = tmp_config_file.getvalue()
                # Use our SafeRClone instead of rclone.with_config
                rclone_instance = SafeRClone(cfg=o)

        # I think that given a file, any file, rclone.with_config() will always
        # return _something_ as it doesn't validate the config file
        if rclone_instance is None:
            raise ConfigFileError("The rclone instance was not created.")

    except FileNotFoundError as err:
        print_error(err)

    return rclone_instance


def rclone_copy(rclone_instance: rclone.RClone, output_dir: str) -> None:
    """
    Calls the rclone copy function via a shell instance and places the
    decrypted files into the output_dir
    """
    # convert list of remotes in str format into a list
    remotes = rclone_instance.listremotes()["out"].decode().splitlines()

    for r in remotes:
        logger.info(f"Copying and decrypting: {r}")
        result = rclone_instance.copy(f"{r}", f"{output_dir}")
        if result["code"] != 0:
            error_msg = result["error"].decode("utf-8").strip()
            logger.warning(f"Failed to decrypt {r}. Rclone error: {error_msg}")


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
            normalized_temp_dir = temp_dir_name.replace(os.sep, "/")
            rclone_instance = get_rclone_instance(
                config, files, normalized_temp_dir
            )

            if rclone_instance is None:
                raise ConfigFileError("rclone_instance cannot be None")

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
                rclone_copy(rclone_instance, output_dir)
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
