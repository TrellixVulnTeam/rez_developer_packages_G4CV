name = "rez_pip_boy"

version = "2.2.0"

description = "Convert an installed pip package back into a source package"

authors = [
    "Colin Kennedy",
]

help = [["README", "README.md"]]

private_build_requires = ["rez_build_helper-1+<2"]

build_command = "python -m rez_build_helper --items bin python"

requires = [
    "python-2.7+<3.8",
    "rez-2.47+<3",
    "rez_utilities-2+<3",
    "wurlitzer-2+<3",
]

tests = {
    "black_diff": {
        "command": "black --diff --check package.py python tests",
        "requires": ["black-19.10+<20"],
    },
    "black": {
        "command": "black package.py python tests",
        "requires": ["black-19.10+<20"],
        "run_on": "explicit",
    },
    "coverage": {
        "command": (
            "coverage erase "
            "&& coverage run --parallel-mode -m unittest discover "
            "&& coverage combine --append "
            "&& coverage html"
        ),
        "requires": ["coverage-5+<6", "mock-3+<4", "six-1.14+<2"],
        "run_on": "explicit",
    },
    "isort": {
        "command": "isort --recursive package.py python tests",
        "requires": ["isort-4.3+<5"],
        "run_on": "explicit",
    },
    "isort_check": {
        "command": "isort --check-only --diff --recursive package.py python tests",
        "requires": ["isort-4.3+<5"],
    },
    "pydocstyle": {
        # Need to disable D202 for now, until a new pydocstyle version is released
        # Reference: https://github.com/psf/black/issues/1159
        #
        "command": "rez-env pydocstyle -- pydocstyle --ignore=D202,D203,D213,D406,D407 python tests/*"
    },
    "pylint": {
        "command": "pylint --disable=bad-continuation python/rez_pip_boy tests",
        "requires": ["pylint-1.9+<2"],
    },
    "unittest_python_2": {
        "command": "python -m unittest discover",
        "requires": ["mock-3+<5", "python-2", "six-1.14+<2",],
    },
    "unittest_python_3": {
        "command": "python -m unittest discover",
        "requires": ["python-3.6", "six-1.14+<2",],
    },
}

uuid = "a1ad023d-c7f3-49be-a3e8-250be6590699"


def commands():
    import os
    import platform

    env.PATH.append(os.path.join("{root}", "bin"))
    env.PYTHONPATH.append(os.path.join("{root}", "python"))

    tar_location = os.getenv("PIP_BOY_TAR_LOCATION", "")

    if not tar_location:
        if any(platform.win32_ver()):
            env.PIP_BOY_TAR_LOCATION.set(os.path.join("C:", "tarred_rez_packages"))
        else:
            env.PIP_BOY_TAR_LOCATION.set(os.path.join("/tmp", "tarred_rez_packages"))
