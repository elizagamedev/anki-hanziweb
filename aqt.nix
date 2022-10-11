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
  version = "2.1.54";

  anki = buildPythonPackage rec {
    pname = "anki";
    inherit version;
    format = "wheel";

    src = fetchPypi {
      inherit pname version format;
      dist = "cp39";
      python = "cp39";
      abi = "abi3";
      platform = "manylinux_2_28_x86_64";
      hash = "sha256-u4ExD0Ukpjlfl67sYp1cKHQEuIIMV0dAboUlG7oG26w=";
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
    hash = "sha256-7gWjmxm+D8NsnrLjlFidLvrdGCAzNRYAzsXapEJGL2U=";
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
