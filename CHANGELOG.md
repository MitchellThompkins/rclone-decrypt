# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Changed
- Removes dependency on build-app on test completion
- Added job to allow tests to run on macos
- Added `hook-tkinterdnd2.py` file to allow pyinstaller to install all
  necessary tkinterdnd2 files
- Modified build-app to install dependencies for pyinstaller
- Added settings to force venv to be generated in the project directory
- Removed geometry specification from file, instead let tk decide the window
  size
- Updates checkout to v3

## [0.1.1] - 2021-04-28
### Changed
- Updated links in changelog
- Checks version info in unit tests
- Hopefully fixes pypi repo information


## [0.1.0] - 2021-04-28
### Added
- Initial release of rclone-decrypt, see
[README.md](https://github.com/MitchellThompkins/rclone-decrypt/blob/v0.1.0/README.md)
for feature details

[unreleased]: https://github.com/mitchellthompkins/rclone-decrypt/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/mitchellthompkins/rclone-decrypt/releases/tag/v0.1.1
[0.1.0]: https://github.com/mitchellthompkins/rclone-decrypt/releases/tag/v0.1.0

