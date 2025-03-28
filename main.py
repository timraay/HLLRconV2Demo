import asyncio
import importlib
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][%(module)s.%(funcName)s:%(lineno)s] %(message)s',
)

def print_error(*args):
    if not args:
        print()
    else:
        print('\033[91m', end='')
        print(*args, end='')
        print('\033[0m')

def main():
    if len(sys.argv) == 1:
        print_error("Missing parameter: Please specify a demo")
        return
    
    module_name = sys.argv[1]
    try:
        module = importlib.import_module(f"demos.{module_name}")
    except ModuleNotFoundError:
        print_error("Unknown demo: %s" % module_name)
        return

    if asyncio.iscoroutinefunction(module.main):
        asyncio.run(module.main())
    else:
        module.main()

if __name__ == '__main__':
    main()