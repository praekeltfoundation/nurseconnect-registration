import os


def pytest_addoption(parser):
    parser.addoption(
        "--ncreg-image",
        action="store",
        default=os.environ.get(
            "NCREG_IMAGE", "praekeltfoundation/nurseconnect-registration:develop"
        ),
        help="NurseConnect Registration image to test",
    )


def pytest_report_header(config):
    return "NurseConnect Registration Docker image:{}".format(
        config.getoption("--ncreg-image")
    )
