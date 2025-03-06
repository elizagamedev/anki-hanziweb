# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2025-03-05
### Changed
- If all `click_*_action` options are set to `":none"`, JavaScript will not be
  injected into note types, and all any Hanzi Web JS already on those note types
  will be removed.

### Fixed
- Initial injection of Hanzi Web JS was incorrect. Rerunning Hanzi Web is enough
  to correct the error, even without upgrading to 1.3.1.

## [1.3.0] - 2025-03-04
### Added
- Multiple click actions can now be specified in a context menu.

### Fixed
- Shinjitai to kyūjitai conversion strips HTML and Anki-style ruby text (for
  example, 振[ふ]り 仮名[がな]). HTML ruby text is still not processed
  correctly.

## [1.2.0] - 2025-03-02
### Added
- New options `click_*_action` which allow Hanzi Web to be interactively
  clickable.

### Changed
- UI tweaked to use space more efficiently on smaller screens.

## [1.1.2] - 2025-01-24
### Fixed
- Fixed bug introduced in 1.1.0 where cards classified as "relearning" would
  cause a crash.

## [1.1.1] - 2025-01-24
### Fixed
- Fixed bug introduced in 1.1.0 where new cards weren't updated when
  `days_to_update` was set to 0.

## [1.1.0] - 2025-01-24
### Added
- On'yomi are differentiated by go'on, kan'on, etc.
- New configuration option `days_to_update` which, when set, updates only the
  next N days worth of notes.
- Sort by nearest due card rather than latest reviewed. (An Anki update caused a
  massive performance issue with accessing the latest reviewed date.)

### Fixed
- The sorting of cross-referenced notes is now stable, making web entries
  deterministic, i.e., running Hanzi Web multiple times always produces the same
  results.

## [1.0.0] - 2023-05-24
### Added
- Chinese phonetic series and on'yomi information added to output.
- Conversion from shinjitai to kyujitai forms for Japanese terms.
- Option to automatically run Hanzi Web on sync.

### Changed
- Hanzi Web output is now a `table`, not a list.

## [0.1.2] - 2022-10-18
### Added
- Hanzi Web actions can now be undone.

### Fixed
- Main window properly refreshes after updating notes.

## [0.1.1] - 2022-10-14
### Added
- The numbers of known/total hanzi are shown in the report.

### Fixed
- Fixed typo in generated HTML.

## [0.1.0] - 2022-10-12
### Added
- Initial release.

[Unreleased]: https://github.com/elizagamedev/anki-hanziweb/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/elizagamedev/anki-hanziweb/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/elizagamedev/anki-hanziweb/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/elizagamedev/anki-hanziweb/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/elizagamedev/anki-hanziweb/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/elizagamedev/anki-hanziweb/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/elizagamedev/anki-hanziweb/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/elizagamedev/anki-hanziweb/compare/v0.1.2...v1.0.0
[0.1.2]: https://github.com/elizagamedev/anki-hanziweb/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/elizagamedev/anki-hanziweb/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/elizagamedev/anki-hanziweb/releases/tag/v0.1.0
