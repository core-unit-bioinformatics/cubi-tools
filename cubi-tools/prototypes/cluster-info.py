#!/usr/bin/env python3

import abc
import argparse as argp
import collections as col
import datetime as dt
import difflib as diffl
import enum
import functools as fnt
import json
import pathlib as pl
import random as rand
import re
import statistics as stats
import subprocess as sp
import sys

try:
    import toml
    _TOML_AVAILABLE = True
except ImportError:
    _TOML_AVAILABLE = False
    warn_msg = (
        "\nWarning: package 'toml' is not available in the current environment.\n"
        "The reported version of this script is not accurate.\n"
    )
    sys.stderr.write(warn_msg)


__version__ = None
__prog__ = "cluster-info.py"


SetStatistics = col.namedtuple("SetStatistics", ["size", "min", "median", "mode", "max"])


class MemoryUnit(enum.Enum):
    byte = 3
    b = 3
    kilobyte = 2
    kilo = 2
    kibi = 2
    kib = 2
    kb = 2
    k = 2
    megabyte = 1
    mega = 1
    mebi = 1
    mb = 1
    m = 1
    gigabyte = 0
    giga = 0
    gibi = 0
    gib = 0
    gb = 0
    g = 0


class NodeState(enum.Enum):
    offline = 1
    unknown = 1
    down = 1
    stateunknown = 1
    invalid = 2
    online = 0
    free = 0
    jobbusy = 0
    various = 0


class Infrastructure(abc.ABC):

    def convert_ts(self, timestamp):
        try:
            ts = dt.datetime.fromtimestamp(timestamp)
        except TypeError:
            ts = dt.datetime.today()
        ts = ts.strftime("%Y-%m-%dT%H:%M:%S")
        return ts

    def percent(self, enumerator, denominator, precision=1):
        pct = round(enumerator / denominator * 100, precision)
        return pct


class PBSCluster(Infrastructure):
    __slots__ = ("name", "pbs_version", "pbs_server", "timestamp", "node_list")

    def __init__(self, cluster_name, node_infos, correct_smt=False):

        self.name = cluster_name
        self.pbs_version = node_infos["pbs_version"]
        self.pbs_server = node_infos["pbs_server"]
        self.timestamp = self.convert_ts(node_infos["timestamp"])
        self.node_list = [
            ClusterNode(node_name, node_info, correct_smt)
            for node_name, node_info in node_infos["nodes"].items()
        ]
        if self.name == "infer":
            self.name = self._infer_cluster_name()
        return None

    def __repr__(self):

        _online_list = [node for node in self.node_list if node.state.value == 0]

        total_nodes = len(self.node_list)
        cpu_nodes = sum(1 if node.type == "cpu" else 0 for node in self.node_list)
        gpu_nodes = sum(1 if node.type == "gpu" else 0 for node in self.node_list)
        online_nodes = len(_online_list)
        online_cpu_nodes = sum(1 if node.type == "cpu" else 0 for node in _online_list)
        online_gpu_nodes = sum(1 if node.type == "gpu" else 0 for node in _online_list)
        total_memory = sum(node.rsrc_machine["memory_gb"] for node in self.node_list)
        online_memory = sum(node.rsrc_machine["memory_gb"] for node in _online_list)
        total_cpu = sum(node.rsrc_machine["cpu_cores"] for node in self.node_list)
        online_cpu_cores = sum(node.rsrc_machine["cpu_cores"] for node in _online_list)
        total_gpu = sum(node.rsrc_machine["gpu_boards"] for node in self.node_list)
        online_gpu_boards = sum(node.rsrc_machine["gpu_boards"] for node in _online_list)

        cluster_status = (
            f"\n=== Cluster status {self.name} at {self.timestamp}\n"
            f"Total nodes: {total_nodes} (online {online_nodes} "
            f"/ {self.percent(online_nodes, total_nodes)}%)\n"
            f"--- CPU nodes: {cpu_nodes} (online {online_cpu_nodes} "
            f"/ {self.percent(online_cpu_nodes, cpu_nodes)}%)\n"
            f"--- GPU nodes: {gpu_nodes} (online {online_gpu_nodes} "
            f"/ {self.percent(online_gpu_nodes, online_gpu_nodes)}%)\n"
            f"Total CPU cores: {total_cpu} (online: {online_cpu_cores} "
            f"/ {self.percent(online_cpu_cores, total_cpu)}%)\n"
            f"Total memory (GiB): {total_memory} (online {online_memory} "
            f"/ {self.percent(online_memory, total_memory)}%)\n"
            f"Total GPU boards: {total_gpu} (online {online_gpu_boards} "
            f"/ {self.percent(online_gpu_boards, total_gpu)}%)\n"
        )
        return cluster_status

    def _infer_cluster_name(self):

        rand.seed()

        guesses = 2
        results = set()
        while guesses > 0:
            random_node = rand.choice(range(0, len(self.node_list)))
            compare_name = self.node_list[random_node].id
            differ = diffl.SequenceMatcher()
            differ.set_seq2(compare_name)
            count_matches = col.Counter()
            for node in self.node_list:
                if node.id == compare_name:
                    continue
                differ.set_seq1(node.id)
                match = differ.find_longest_match(
                    0, len(node.id), 0, len(compare_name)
                )
                if match.size == 0:
                    continue
                count_matches[node.id[match.b:match.b+match.size]] += 1
            most_common = count_matches.most_common(1)[0][0]
            results.add(most_common)
            guesses -= 1
        if len(results) > 1:
            sys.stderr.write("\nCannot unambiguously infer cluster name - assigning any\n")
        return results.pop()

    def print_node_list(self, node_type, node_state, sort_order, sort_priority, top_n):

        if node_state == "all":
            state_filter = lambda node: True
        elif node_state == "online":
            state_filter = lambda node: node.state == NodeState.online
        elif node_state == "offline":
            state_filter = lambda node: node.state == NodeState.offline
        else:
            raise

        if node_type == "all":
            type_filter = lambda node: True
        elif node_type == "cpu":
            type_filter = lambda node: node.type == "cpu"
        elif node_type == "gpu":
            type_filter = lambda node: node.type == "gpu"
        else:
            raise

        show_nodes = list(filter(state_filter, self.node_list))
        show_nodes = list(filter(type_filter, show_nodes))

        if sort_order == "name":
            show_nodes = sorted(show_nodes, key=lambda node: node.id)
        elif sort_order == "size":
            show_nodes = sorted(show_nodes, reverse=True)
        elif sort_order == "free":
            show_nodes = sorted(
                show_nodes, reverse=True,
                key=lambda node: node._get_free(sort_priority)
            )
        else:
            raise

        factor = -1 if top_n == 0 else 1
        for n, node in enumerate(show_nodes, start=1):
            if n*factor > top_n:
                break
            print(node)

        return

    def summarize_queue_resources(self, node_state, rsrc_type="machine"):

        if node_state == "all":
            state_filter = lambda node: True
        elif node_state == "online":
            state_filter = lambda node: node.state == NodeState.online
        elif node_state == "offline":
            state_filter = lambda node: node.state == NodeState.offline
        else:
            raise

        show_nodes = list(filter(state_filter, self.node_list))

        summary = dict()

        for node in show_nodes:
            cpu, mem, gpu = node._get_rsrc() if rsrc_type == "machine" else node._get_free()
            for qlist in node.queue_list:
                if qlist not in summary:
                    summary[qlist] = col.defaultdict(list)
                summary[qlist]["cpu"].append(cpu)
                summary[qlist]["mem"].append(mem)
                summary[qlist]["gpu"].append(gpu)

        queue_report = f"\nResource summary (state: {rsrc_type}) for cluster {self.name}\n"
        for qlist in sorted(summary.keys()):
            resources = summary[qlist]
            queue_report += f"Qlist: {qlist}\n"
            for rsrc_name, out_label in zip(["cpu", "mem", "gpu"], ["CPU[cores]", "MEM[gb]", "GPU[boards]"]):
                rsrc_values = resources[rsrc_name]
                value_stats = self._compute_stats(rsrc_values)
                if rsrc_name == "cpu":
                    queue_report += (
                        f"Nodes: {value_stats.size}\n"
                        f"--- min / median / mode / max ---\n"
                    )
                queue_report += (
                    f"{out_label}: "
                    f"{value_stats.min} / "
                    f"{value_stats.median} / "
                    f"{value_stats.mode} / "
                    f"{value_stats.max}\n"
                )
            queue_report += "---------------------------------\n"

        return queue_report

    def _compute_stats(self, rsrc_list):

        size = len(rsrc_list)
        min_val = min(rsrc_list)
        median_val = int(stats.median(rsrc_list))
        mode_val = stats.mode(rsrc_list)
        max_val = max(rsrc_list)

        set_stats = SetStatistics(
            size, min_val, median_val, mode_val, max_val
        )

        return set_stats


@fnt.total_ordering
class ClusterNode(Infrastructure):
    __slots__ = (
        "id", "scheduler", "state", "type",
        "last_used", "last_state_change",
        "queue_list", "workloads", "load_estimate",
        "job_list",
        "rsrc_machine", "rsrc_used", "rsrc_remain",
    )

    def __init__(self, node_name, node_infos, correct_smt=False):

        self.id = node_name
        self.type = None
        self.workloads = None
        self.scheduler = node_infos.get("ntype", "unknown")
        self.state = self._parse_state(node_infos["state"])
        self.last_used = self.convert_ts(
            node_infos.get("last_used_time", 0)
        )
        self.last_state_change = self.convert_ts(
            node_infos.get("last_state_change_time", 0)
        )
        self.job_list = sorted(node_infos.get("jobs", []))

        self.rsrc_machine = self._parse_resource_info(node_infos["resources_available"], True, correct_smt)
        self.rsrc_used = self._parse_resource_info(node_infos["resources_assigned"], correct_smt)

        if self.type is None:
            self.type = "cpu"
            self.workloads = "cpu"

        self._estimate_node_load()

        return None

    def __repr__(self):

        node_status = [
            f"=== node id: {self.id}",
            f"node state: {self.state.name}",
            f"node associated queues/Qlist resource: {self.queue_list}",
            f"node load estimate: {self.load_estimate}",
            f"node type/workloads: {self.type}",
            f"node architecture: {self.rsrc_machine['cpu_microarchitecture']}",
            f"node cpu cores: {self.rsrc_machine['cpu_cores']} (free: {self.rsrc_remain['cpu_cores']})",
            f"node memory gb: {self.rsrc_machine['memory_gb']} (free: {self.rsrc_remain['memory_gb']})",

        ]
        if self.type == "gpu":
            node_status.extend(
                [
                    f"node gpu boards: {self.rsrc_machine['gpu_boards']} (free: {self.rsrc_remain['gpu_boards']})",
                    f"node gpu boards model: {self.rsrc_machine['gpu_model']}"
                ]
            )
        node_status = "\n".join(node_status) + "\n"

        return node_status

    def __eq__(self, other):
        same_cpu = self.rsrc_machine["cpu_cores"] == other.rsrc_machine["cpu_cores"]
        same_mem = self.rsrc_machine["memory_gb"] == other.rsrc_machine["memory_gb"]
        same_gpu = self.rsrc_machine["gpu_boards"] == other.rsrc_machine["gpu_boards"]
        return same_cpu and same_mem and same_gpu

    def __lt__(self, other):
        less_cpu = self.rsrc_machine["cpu_cores"] < other.rsrc_machine["cpu_cores"]
        less_mem = self.rsrc_machine["memory_gb"] < other.rsrc_machine["memory_gb"]
        less_equal_gpu = self.rsrc_machine["gpu_boards"] <= other.rsrc_machine["gpu_boards"]
        return less_cpu or less_mem and less_equal_gpu

    def __gt__(self, other):
        more_cpu = self.rsrc_machine["cpu_cores"] > other.rsrc_machine["cpu_cores"]
        more_mem = self.rsrc_machine["memory_gb"] > other.rsrc_machine["memory_gb"]
        more_equal_gpu = self.rsrc_machine["gpu_boards"] >= other.rsrc_machine["gpu_boards"]
        return more_cpu or more_mem and more_equal_gpu

    def _norm_mem_to_gibi(self, memory, blunt=True):
        mem_value = re.search("[0-9]+", memory)
        mem_unit = re.search("[mkgb]+", memory.lower())
        if mem_value is None:
            raise ValueError(f"Invalid memory expression: {memory}")
        mem_value = int(mem_value.group(0))
        if mem_unit is None:
            # memory can be just a number,
            # then we assume it's byte
            mem_unit = MemoryUnit["byte"]
        else:
            mem_unit = MemoryUnit[mem_unit.group(0)]
        power = mem_unit.value
        mem_gibi = mem_value / 1024 ** power
        if blunt:
            mem_gibi = int(round(mem_gibi, 0))
        else:
            mem_gibi = round(mem_gibi, 2)
        return mem_gibi

    def _parse_state(self, state_expr):

        all_states = [
            se.replace("-", "") for se in state_expr.split(",")
        ]
        node_state = set(NodeState[s.strip().strip("<>")] for s in all_states)
        if len(node_state) != 1:
            warn_msg = f"\nWarning: invalid node state: {state_expr} / {self.id}\n"
            sys.stderr.write(warn_msg)
            node_state = NodeState["invalid"]
        else:
            node_state = node_state.pop()
            if node_state == "<various>":
                warn_msg = f"\nWarning: undefined node state: {state_expr} / {self.id}\n"
                sys.stderr.write(warn_msg)
                node_state = NodeState["various"]
        return node_state

    def _parse_resource_info(self, resource_info, assert_minimal_set=False, correct_smt=False):

        machine_resources = []
        for rsrc_key, rsrc_value in resource_info.items():
            try:
                norm_value = rsrc_value.strip().lower()
            except AttributeError:
                if isinstance(rsrc_value, int):
                    norm_value = rsrc_value
                else:
                    raise ValueError(f"{rsrc_key} --- {rsrc_value} (norm failed)")
            if rsrc_key in ["accelerator_model", "gpu_id"]:
                if rsrc_value == "none":
                    self.workloads = "cpu"
                    self.type = "cpu"
                    gpu_model = "igpu"
                else:
                    self.workloads = "gpu"
                    self.type = "gpu"
                    gpu_model = norm_value
                machine_resources.append(("gpu_model", gpu_model))
            if rsrc_key == "arch":
                # fix (for the time being)
                # currently, in the M-HPC, arch is always linux
                # which does not carry any information
                if norm_value != "linux":
                    machine_resources.append(("cpu_microarchitecture", norm_value))
                else:
                    machine_resources.append(("cpu_microarchitecture", "unknown"))
            if rsrc_key == "host":
                assert norm_value == self.id
            if rsrc_key == "ncpus":
                if correct_smt:
                    cpu_cores = int(norm_value) // 2
                else:
                    cpu_cores = int(norm_value)
                machine_resources.append(("cpu_cores", cpu_cores))
            if rsrc_key == "ngpus":
                machine_resources.append(("gpu_boards", int(norm_value)))
            if rsrc_key == "mem":
                machine_resources.append(("memory_gb", self._norm_mem_to_gibi(norm_value)))
            if rsrc_key in ["Qlist", "qlist"]:
                self.queue_list = norm_value.split(",")

        machine_resources = col.OrderedDict(
            sorted(machine_resources)
        )

        if assert_minimal_set:
            minimal_rsrc_set = ["cpu_cores", "gpu_boards", "memory_gb"]
            for key in minimal_rsrc_set:
                try:
                    _ = machine_resources[key]
                except KeyError:
                    machine_resources[key] = 0

        return machine_resources

    def _estimate_node_load(self):

        consider_keys = ["cpu_cores", "gpu_boards", "memory_gb"]
        rsrc_remain = col.OrderedDict()
        load_values = []
        for rsrc_key, rsrc_value in self.rsrc_machine.items():
            if rsrc_key not in consider_keys:
                continue
            try:
                rsrc_used = self.rsrc_used[rsrc_key]
            except KeyError:
                self.rsrc_used[rsrc_key] = 0
                rsrc_used = 0
            rsrc_remain[rsrc_key] = max(0, rsrc_value - rsrc_used)
            if rsrc_value == 0:
                # NB: CPU servers have no GPU boards
                assert self.workloads == "cpu", f"{rsrc_key} / {rsrc_value}: {self.rsrc_machine}"
            else:
                load_value = rsrc_used / rsrc_value
                load_values.append(load_value)
        self.rsrc_remain = rsrc_remain
        load_estimate = round(sum(load_values) / len(load_values), 2)
        self.load_estimate = load_estimate
        return

    def _get_rsrc(self):

        rsrc_cpu = self.rsrc_machine["cpu_cores"]
        rsrc_gpu = self.rsrc_machine["gpu_boards"]
        rsrc_mem = self.rsrc_machine["memory_gb"]

        return rsrc_cpu, rsrc_mem, rsrc_gpu

    def _get_free(self, priority="cpu"):

        assert priority in ["cpu", "gpu", "mem"]

        free_cpu = self.rsrc_remain["cpu_cores"]
        free_gpu = self.rsrc_remain["gpu_boards"]
        free_mem = self.rsrc_remain["memory_gb"]

        if free_cpu < 1 or free_mem < 2:
            free_rsrc = -1,-1,-1

        if priority == "cpu":
            free_rsrc = free_cpu, free_mem, free_gpu
        elif priority == "gpu":
            free_rsrc = free_gpu, free_mem, free_cpu
        else:
            free_rsrc = free_mem, free_cpu, free_gpu

        return free_rsrc


def parse_command_line():

    parser = argp.ArgumentParser(
        prog=__prog__,
        description="Print status summaries for the cluster or all nodes.",
        usage=f"{__prog__}"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=report_script_version(),
        help="Displays version of this script.",
    )

    parser.add_argument(
        "--node-info", "-i", "-n",
        type=lambda x: pl.Path(x).resolve(strict=True),
        default=None,
        dest="node_info"
    )

    parser.add_argument(
        "--show-node-state", "-state",
        type=str,
        choices=["online", "offline", "all"],
        default="online",
        dest="node_state"
    )

    parser.add_argument(
        "--show-node-type", "-type",
        type=str,
        choices=["cpu", "gpu", "all"],
        default="all",
        dest="node_type"
    )

    parser.add_argument(
        "--show-first-n", "-topn",
        type=int,
        default=0,
        dest="show_first_n",
        help="Show only first N nodes in node listing output (modified by node type and state)."
    )

    parser.add_argument(
        "--node-list", "-nl",
        type=str,
        choices=["name", "size", "free", "no"],
        default="size",
        dest="node_list",
        help=(
            "Print node list sorted by node name, node size (CPU/MEM/GPU), "
            "free resources or do not print node listing."
        )
    )

    parser.add_argument(
        "--free-priority", "-free",
        type=str,
        choices=["cpu", "gpu", "mem"],
        default="cpu",
        dest="free_priority",
        help="If node listing is ordered by 'free' resources, prioritize cpu, gpu or memory."
    )

    parser.add_argument(
        "--cluster-info", "-ci",
        action="store_true",
        default=False,
        dest="cluster_info"
    )

    parser.add_argument(
        "--cluster-name", "-cn",
        type=str,
        default="infer",
        dest="cluster_name"
    )

    parser.add_argument(
        "--correct-smt", "-smt",
        action="store_true",
        default=False,
        dest="correct_smt"
    )

    parser.add_argument(
        "--queue-resources", "-q",
        type=str,
        default=None,
        choices=["machine", "free"],
        dest="queue_resources"
    )

    args = parser.parse_args()

    return args


def evaluate_cluster_status(node_infos, args):

    cluster = PBSCluster(args.cluster_name, node_infos, args.correct_smt)
    if args.node_list != "no":
        cluster.print_node_list(
            args.node_type,
            args.node_state,
            args.node_list,
            args.free_priority,
            args.show_first_n
        )

    if args.cluster_info:
        print(cluster)

    if args.queue_resources is not None:
        print(
            cluster.summarize_queue_resources(
                args.node_state, args.queue_resources
            )
        )

    return


def exec_system_call(call, workfolder=None, fail_on_error=True, return_stdout=False):

    try:
        process_return = sp.run(
            call, cwd=workfolder, check=True,
            stdout=sp.PIPE, stderr=sp.PIPE
        )
    except sp.CalledProcessError:
        if fail_on_error:
            raise
    if return_stdout:
        if process_return.stdout is None:
            value = None
        else:
            value = process_return.stdout.decode("utf-8").strip()
    else:
        value = None
    return value


def find_cubi_tools_top_level():
    """Find the top-level folder of the cubi-tools
    repository (starting from this script path).
    """
    script_path = pl.Path(__file__).resolve(strict=True)
    script_folder = script_path.parent

    git_cmd = ["git", "rev-parse", "--show-toplevel"]
    repo_path = exec_system_call(git_cmd, script_folder, return_stdout=True)
    repo_path = pl.Path(repo_path)
    return repo_path


def report_script_version():
    """
    Read out of the cubi-tools script version out of the 'pyproject.toml'.
    """
    if not _TOML_AVAILABLE:
        # this is somewhat non-standard behavior to make that script work
        # with the python standard library alone
        return "undefined"

    cubi_tools_repo = find_cubi_tools_top_level()

    toml_file = cubi_tools_repo.joinpath("pyproject.toml").resolve(strict=True)

    toml_file = toml.load(toml_file, _dict=dict)
    cubi_tools_scripts = toml_file["cubi"]["tools"]["script"]
    version = None
    for cubi_tool in cubi_tools_scripts:
        if cubi_tool["name"] == __prog__:
            version = cubi_tool["version"]
    if version is None:
        raise RuntimeError(
            f"Cannot identify script version from pyproject cubi-tools::scripts entry: {cubi_tools_scripts}"
        )
    return version


def main():

    args = parse_command_line()

    if args.node_info is None:
        cmd = ["pbsnodes", "-a", "-F", "json"]
        try:
            out = exec_system_call(cmd, fail_on_error=True, return_stdout=True)
        except FileNotFoundError:
            err_msg = (
                "Need command 'pbsnodes' available in $PATH or its output in "
                "JSON format read from a file location specified via "
                "the '--node-info' command line argument."
            )
            raise EnvironmentError(err_msg)
        node_infos = json.loads(out)
    else:
        with open(args.node_info) as dump:
            node_infos = json.load(dump)

    evaluate_cluster_status(node_infos, args)

    return 0



if __name__ == "__main__":
    main()
