import sys
import os, json
import types
import gc
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
import config
logger = hp.get_logger(__name__)


class PluginManager:
    def __init__(self):
        # registry: {service_name: [{variable_name, module_name, service_name}]} — persisted to JSON
        # modules:  {module_name: module_object} — in-memory only
        if os.path.exists("duplicate_services_registry.json"):
            with open("duplicate_services_registry.json", "r") as f:
                self.registry = json.load(f)
        else:
            self.registry = {}
        self.modules = {}

    def _save_registry(self):
        with open("duplicate_services_registry.json", "w") as f:
            json.dump(self.registry, f, indent=4)

    def _find_entry(self, module_name: str):
        """Return (service_name, entry_dict) for a given module_name, or (None, None)."""
        for service_name, entries in self.registry.items():
            for entry in entries:
                if entry["module_name"] == module_name:
                    return service_name, entry
        return None, None

    def create_plugin(self, name: str, code: str, folder: str = None):
        if name in sys.modules:
            raise ValueError(f"Plugin '{name}' already exists")

        if folder:
            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, f"{name}.py")
            with open(file_path, "w") as f:
                f.write(code)

    def delete_service(self, service_name: str):
        """Delete all modules registered under a service name."""
        entries = list(self.registry.get(service_name, []))
        if not entries:
            logger.warning(f"No plugins found for service '{service_name}'")
            return
        for entry in entries:
            self.delete_plugin(entry["module_name"])
        logger.info(f"Deleted all plugins for service '{service_name}'")

    def delete_plugin(self, module_name: str):
        service_name, entry = self._find_entry(module_name)
        if entry is None:
            logger.warning(f"Plugin '{module_name}' not found in registry")
            return

        # delete the physical module file
        file_path = os.path.join(service_name, f"{module_name}.py")
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file '{file_path}'")

        # remove entry from registry and persist
        self.registry[service_name] = [
            e for e in self.registry[service_name] if e["module_name"] != module_name
        ]
        if not self.registry[service_name]:
            del self.registry[service_name]
        self._save_registry()

        # remove worker entry from start_worker_config.json
        if os.path.exists("start_worker_config.json"):
            with open("start_worker_config.json", "r") as f:
                swc = json.load(f)
            swc["workers"] = [
                w for w in swc["workers"] if w.get("entry_point") != f"{module_name}.py"
            ]
            with open("start_worker_config.json", "w") as f:
                json.dump(swc, f, indent=4)
                f.write('\n')

        # remove the config variable line from config.py
        variable_name = entry["variable_name"]
        if os.path.exists("config.py"):
            with open("config.py", "r") as f:
                lines = f.readlines()
            filtered = [l for l in lines if not l.strip().startswith(f"{variable_name} =")]
            while filtered and filtered[-1].strip() == '':
                filtered.pop()
            with open("config.py", "w") as f:
                f.writelines(filtered)
                f.write('\n')
        if hasattr(config, variable_name):
            delattr(config, variable_name)

        logger.info(f"Deleted plugin '{module_name}' (service '{service_name}')")

    def list_plugins(self):
        """Return a flat list of all entry dicts across all services."""
        entries = []
        for service_name, service_entries in self.registry.items():
            for entry in service_entries:
                entries.append({**entry, "service_key": service_name})
        return entries

    def create_gryd_service(self, service_name: str, service_module : str, main_task: str, num_threads = None):

        """"
        Dynamically create a gryd service module with the given name and main task.
        service_name = foldder_name e.g. voice, campaign, etc.
        service_module = python file containing service definations and main task to run.
        main_task = is the function name (not the name provided in is_a_task deorator).

        """

        logger.info(f"Creating gryd service: service_name={service_name}, service_module={service_module}, main_task={main_task}, num_threads={num_threads}")
        variable_name = f"AUTOCRM_{service_name.upper()}_SERVICE_NAME"
        logger.debug(f"Constructed config variable name: {variable_name}")
        if not hasattr(config, variable_name):
            logger.error(f"Config variable '{variable_name}' not found for service '{service_name}'")
            raise ValueError("service variable  name not found in config")

        new_variable_name = variable_name + '_' + "1"
        iteration = 1
        if self.registry.get(service_name):
            a = self.registry.get(service_name)[-1]
            iteration = int(a["variable_name"].split("_")[-1]) + 1
            new_variable_name = "_".join(a["variable_name"].split("_")[:-1]) + "_" + str(iteration)
            logger.info(f"Duplicate service detected for '{service_name}', iteration={iteration}, new_variable_name={new_variable_name}")

        new_service_name_value = f"{getattr(config, variable_name)}-{iteration}"
        self.new_module_name = service_name + "_" + str(iteration)

        new_entry = {
            "variable_name": new_variable_name,
            "module_name": self.new_module_name,
            "service_name": new_service_name_value
        }

        if self.registry.get(service_name):
            self.registry[service_name].append(new_entry)
            logger.debug(f"Updated duplicate_services_registry.json for '{service_name}'")
        else:
            self.registry[service_name] = [new_entry]
            logger.debug(f"Registered new service '{service_name}' in duplicate_services_registry.json")

        # with open("duplicate_services_registry.json", "w") as f:
        #     json.dump(self.registry, f, indent=4)

        self._save_registry()

        with open("config.py", "a") as f:
            f.write(f'\n{new_variable_name} = os.environ.get("{new_variable_name}", "{new_service_name_value}")')
        logger.info(f"Appended '{new_variable_name}' to config.py")
        setattr(config, new_variable_name, new_service_name_value)
        logger.debug(f"Set config.{new_variable_name} = '{new_service_name_value}' in memory")

        with open("start_worker_config.json", "r") as f:
            start_worker_config = json.load(f)

        x = {}
        for w in start_worker_config["workers"]:
            if w["name"] == service_name:
                x = w
                break

        if x:
            logger.debug(f"Found existing worker config for '{service_name}': {x}")
        else:
            logger.debug(f"No existing worker config found for '{service_name}', using defaults")

        start_worker_config["workers"].append({
            "name": service_name,
            "entry_point": f"{self.new_module_name}.py",
            "gryd_service": new_variable_name,
            "parallel_threads": num_threads or x.get("parallel_threads"),
            "shutdown_time": x.get("shutdown_time", 0)
        })
        with open("start_worker_config.json", "w") as f:
            json.dump(start_worker_config, f, indent=4)
        logger.info(f"Updated start_worker_config.json with new worker entry for '{service_name}'")


        code = (
            f"import {service_module}\n"
            f"from {service_module} import *\n"
            f"import config\n"
            f"import os, sys, json, time\n"
            f"from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp\n"
            f"\n"
            f"gryd.SERVICE = getattr(config, \"{new_variable_name}\")\n"
            f"gryd.set_queue_manager()\n"
            f"\n"
            f"@gryd.is_a_task(function_name=\"{main_task}\")\n"
            f"def {main_task}(*args, **kwargs):\n"
            f"    list({service_module}.{main_task}(*args, **kwargs))\n"
            f"    yield\n"
        )
        logger.info(f"Generated dynamic module code for service '{service_name}' with task '{main_task}'")
        logger.info(f"code: {json.dumps(code, indent=4)}")

        return self.create_plugin(name=self.new_module_name, code=code, folder=service_name)
    




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage gryd services")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a new gryd service")
    p_create.add_argument("--service-name", required=True, help="Service/folder name (e.g. campaign, voice)")
    p_create.add_argument("--service-module", required=True, help="Python module file inside the service folder")
    p_create.add_argument("--main-task", required=True, help="Main task function name")
    p_create.add_argument("--num-threads", type=int, default=None, help="Number of parallel threads (optional)")
    p_create.add_argument("--num-modules", type=int, default=1, help="Number of modules to create (default: 1)")

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a gryd service plugin by module name or all modules for a service")
    p_delete.add_argument("--module-name", help="Module name as registered (e.g. campaign_1)")
    p_delete.add_argument("--service-name", help="Service name to delete all its modules (e.g. campaign)")

    # list
    subparsers.add_parser("list", help="List all registered gryd service plugins")


    args = parser.parse_args()
    manager = PluginManager()

    if args.command == "create":
        for i in range(args.num_modules):
            manager.create_gryd_service(
                service_name=args.service_name,
                service_module=args.service_module,
                main_task=args.main_task,
                num_threads=args.num_threads,
            )
            print(f"Module {i + 1}/{args.num_modules}: Service '{args.service_name}' created successfully.")

    elif args.command == "delete":
        if args.service_name:
            manager.delete_service(args.service_name)
            print(f"All plugins for service '{args.service_name}' deleted.")
        elif args.module_name:
            manager.delete_plugin(args.module_name)
            print(f"Plugin '{args.module_name}' deleted.")
        else:
            print("Error: provide --module-name or --service-name")
            sys.exit(1)

    elif args.command == "list":
        plugins = manager.list_plugins()
        if plugins:
            print(f"{'SERVICE':<20} {'MODULE':<20} {'GRYD SERVICE NAME':<35} {'CONFIG VAR'}")
            print("-" * 95)
            for p in plugins:
                print(f"{p['service_key']:<20} {p['module_name']:<20} {p['service_name']:<35} {p['variable_name']}")
        else:
            print("No plugins registered.")