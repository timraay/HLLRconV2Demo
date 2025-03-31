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
    
    demo_name = sys.argv[1].removesuffix('.py')
    module_name = f"demos.{demo_name}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name and e.name.startswith(module_name):
            print_error("Unknown demo: %s" % demo_name)
            return
        raise

    try:
        if asyncio.iscoroutinefunction(module.main):
            asyncio.run(module.main())
        else:
            module.main()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()