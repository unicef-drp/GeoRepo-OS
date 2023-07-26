import importlib


def module_function(module_name: str, package_name: str, function_name: str):
    package = importlib.import_module(
        f'modules.{module_name}.{package_name}'
    )
    function = getattr(package, function_name)
    return function
