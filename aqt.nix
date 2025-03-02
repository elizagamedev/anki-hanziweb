{ buildPythonPackage
, lib
, fetchPypi
, anki
, beautifulsoup4
, decorator
, distro
, flask
, flask-cors
, jsonschema
, markdown
, orjson
, protobuf
, psutil
, pyqt5
, pyqtwebengine
, requests
, send2trash
, waitress
}:

let
  version = "25.02";

  anki = buildPythonPackage rec {
    pname = "anki";
    inherit version;
    format = "wheel";

    src = fetchPypi {
      inherit pname version format;
      dist = "cp39";
      python = "cp39";
      abi = "abi3";
      platform = "manylinux_2_35_x86_64";
      hash = "sha256-0OvvnY9zCKlyg1ciAXDaj2VYqg3/dy/SM3QABPBxf0E=";
    };

    propagatedBuildInputs = [
      beautifulsoup4
      decorator
      distro
      markdown
      orjson
      protobuf
      requests
    ];

    doCheck = false;
  };
in
buildPythonPackage rec {
  pname = "aqt";
  inherit version;
  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-fTxxXV/8zKebG9OVQiUbiT3QW1wy7vH/HEOtGle+1IM=";
  };

  propagatedBuildInputs = [
    anki
    beautifulsoup4
    requests
    send2trash
    jsonschema
    flask
    flask-cors
    waitress
    pyqt5
    pyqtwebengine
  ];

  doCheck = false;

  meta = with lib; {
    description = "Anki API";
    homepage = "https://pypi.org/project/aqt/";
    license = licenses.agpl3Plus;
  };
}
