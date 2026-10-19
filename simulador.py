"""Parser, generador y motor de simulación del proyecto de paginación."""

from dataclasses import dataclass
import random
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from mmu import FIFO, LFU, LRU, OPT, SecondChance, MMU


ALGORITHMS = {
    "FIFO": FIFO,
    "SC": SecondChance,
    "SECOND CHANCE": SecondChance,
    "LRU": LRU,
    "LFU": LFU,
    "OPT": OPT,
}

OPERATION_RE = re.compile(
    r"^\s*(new|use|delete|kill)\s*\(\s*([^)]*)\s*\)\s*(?:#|//|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Operation:
    """Una instrucción de proceso en el formato del anexo."""

    command: str
    pid: int
    value: Optional[int] = None

    def __str__(self) -> str:
        if self.command == "new":
            return f"new({self.pid},{self.value})"
        if self.command == "use" or self.command == "delete":
            return f"{self.command}({self.value})"
        return f"kill({self.pid})"


def parse_operations(text: str) -> List[Operation]:
    """Parsea el archivo del anexo y valida sus referencias básicas."""
    operations: List[Operation] = []
    known_ptrs: Dict[int, int] = {}
    next_ptr = 1
    killed = set()

    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        match = OPERATION_RE.match(line)
        if not match:
            raise ValueError(f"Línea {line_number}: operación inválida")

        command = match.group(1).lower()
        arguments = [item.strip() for item in match.group(2).split(",") if item.strip()]
        try:
            if command == "new":
                if len(arguments) != 2:
                    raise ValueError("new requiere pid y tamaño")
                pid, size = (int(item) for item in arguments)
                if pid in killed:
                    raise ValueError("el proceso ya fue terminado")
                if size <= 0:
                    raise ValueError("el tamaño debe ser positivo")
                known_ptrs[next_ptr] = pid
                operations.append(Operation("new", pid, size))
                next_ptr += 1
            elif command in ("use", "delete"):
                if len(arguments) != 1:
                    raise ValueError(f"{command} requiere un puntero")
                ptr = int(arguments[0])
                if ptr not in known_ptrs:
                    raise ValueError(f"el puntero {ptr} no existe")
                pid = known_ptrs[ptr]
                operations.append(Operation(command, pid, ptr))
                if command == "delete":
                    del known_ptrs[ptr]
            else:
                if len(arguments) != 1:
                    raise ValueError("kill requiere un PID")
                pid = int(arguments[0])
                if pid in killed:
                    raise ValueError("el proceso ya fue terminado")
                operations.append(Operation("kill", pid))
                killed.add(pid)
                for ptr, owner in list(known_ptrs.items()):
                    if owner == pid:
                        del known_ptrs[ptr]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Línea {line_number}: {exc}") from exc

    _validate_process_order(operations)
    return operations


def _validate_process_order(operations: Sequence[Operation]) -> None:
    killed = set()
    for operation in operations:
        if operation.command == "new" and operation.pid in killed:
            raise ValueError(f"El proceso {operation.pid} usa new después de kill")
        if operation.command == "kill":
            killed.add(operation.pid)


def operations_to_text(operations: Iterable[Operation]) -> str:
    return "\n".join(str(operation) for operation in operations) + "\n"


def generate_operations(
    seed: int,
    process_count: int,
    operation_count: int,
) -> List[Operation]:
    if process_count not in (10, 50, 100):
        raise ValueError("La cantidad de procesos debe ser 10, 50 o 100")
    if operation_count not in (500, 1000, 5000):
        raise ValueError("La cantidad de operaciones debe ser 500, 1000 o 5000")

    rng = random.Random(seed)
    live: Dict[int, List[int]] = {pid: [] for pid in range(1, process_count + 1)}
    killed = set()
    next_ptr = 1
    operations: List[Operation] = []

    for _ in range(operation_count):
        candidates = [pid for pid in live if pid not in killed]
        pid = rng.choice(candidates)
        choices = ["new"]
        if live[pid]:
            choices.extend(("use", "delete"))
        if live[pid] and len(operations) < operation_count - 1 and len(candidates) > 1:
            choices.append("kill")
        command = rng.choice(choices)

        if command == "new":
            size = rng.randint(1, 12 * 1024)
            live[pid].append(next_ptr)
            operations.append(Operation("new", pid, size))
            next_ptr += 1
        elif command == "use":
            operations.append(Operation("use", pid, rng.choice(live[pid])))
        elif command == "delete":
            ptr = rng.choice(live[pid])
            live[pid].remove(ptr)
            operations.append(Operation("delete", pid, ptr))
        else:
            operations.append(Operation("kill", pid))
            killed.add(pid)

    return operations


def _page_references(operations: Sequence[Operation]) -> List[int]:
    next_page = 1
    ptr_pages: Dict[int, List[int]] = {}
    ptr_owner: Dict[int, int] = {}
    references: List[int] = []
    next_ptr = 1
    for operation in operations:
        if operation.command == "new":
            count = (operation.value + 4095) // 4096
            pages = list(range(next_page, next_page + count))
            next_page += count
            ptr_pages[next_ptr] = pages
            ptr_owner[next_ptr] = operation.pid
            references.extend(pages)
            next_ptr += 1
        elif operation.command == "use":
            references.extend(ptr_pages[operation.value])
        elif operation.command == "delete":
            ptr_pages.pop(operation.value)
            ptr_owner.pop(operation.value, None)
        elif operation.command == "kill":
            owner_ptrs = [
                ptr for ptr, owner in ptr_owner.items() if owner == operation.pid
            ]
            for ptr in owner_ptrs:
                ptr_pages.pop(ptr, None)
                ptr_owner.pop(ptr, None)
    return references


def _algorithm_factory(name: str, references: Sequence[int]):
    normalized = name.strip().upper()
    if normalized not in ALGORITHMS:
        raise ValueError(f"Algoritmo no soportado: {name}")
    algorithm = ALGORITHMS[normalized]
    return algorithm(references) if algorithm is OPT else algorithm()


class Simulation:

    def __init__(self, operations: Sequence[Operation], algorithm: str):
        self.operations = list(operations)
        self.algorithm_name = algorithm
        references = _page_references(self.operations)
        self.mmus = {
            "OPT": MMU(_algorithm_factory("OPT", references)),
            algorithm.upper(): MMU(_algorithm_factory(algorithm, references)),
        }
        self.elapsed = {"OPT": 0, algorithm.upper(): 0}
        self.thrashing = {"OPT": 0, algorithm.upper(): 0}
        self.history: List[dict] = []
        self.index = 0
        self.paused = False

    @property
    def selected_key(self) -> str:
        return self.algorithm_name.upper()

    def step(self) -> dict:
        if self.index >= len(self.operations):
            raise StopIteration("La simulación ya terminó")
        if self.paused:
            raise RuntimeError("La simulación está pausada")

        operation = self.operations[self.index]
        result = {"operation": operation, "algorithms": {}}
        for name, mmu in self.mmus.items():
            value = self._execute(mmu, operation)
            pages = len(value["hits"]) + len(value["faults"])
            elapsed = len(value["hits"]) + 5 * len(value["faults"])
            self.elapsed[name] += elapsed
            self.thrashing[name] += 5 * len(value["faults"])
            result["algorithms"][name] = {
                "access": value,
                "elapsed": self.elapsed[name],
                "thrashing": self.thrashing[name],
                "state": mmu.get_state(),
                "pages_accessed": pages,
            }
        self.history.append(result)
        self.index += 1
        return result

    @staticmethod
    def _execute(mmu: MMU, operation: Operation) -> dict:
        if operation.command == "new":
            ptr = mmu.new(operation.pid, operation.value)
            return {"hits": [], "faults": mmu.last_access["faults"], "ptr": ptr}
        if operation.command == "use":
            return mmu.use(operation.value)
        if operation.command == "delete":
            mmu.delete(operation.value)
            return {"hits": [], "faults": []}
        mmu.kill(operation.pid)
        return {"hits": [], "faults": []}

    def run(self) -> List[dict]:
        while self.index < len(self.operations):
            self.step()
        return self.history

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def snapshot(self) -> dict:
        return {
            "index": self.index,
            "total_operations": len(self.operations),
            "finished": self.index == len(self.operations),
            "paused": self.paused,
            "algorithms": {
                name: self.metrics(mmu, name)
                for name, mmu in self.mmus.items()
            },
        }

    def metrics(self, mmu: MMU, name: str) -> dict:
        resident = sum(page["in_ram"] for page in mmu.pages.values())
        total = len(mmu.pages)
        used_bytes = total * mmu.page_size
        virtual_bytes = (total - resident) * mmu.page_size
        internal = sum(
            len(allocation["pages"]) * mmu.page_size - allocation["size"]
            for allocation in mmu.ptrs.values()
        )
        active = sum(
            not process["terminated"] and bool(process["ptrs"])
            for process in mmu.processes.values()
        )
        elapsed = self.elapsed[name]
        thrashing = self.thrashing[name]
        return {
            "ram_pages": resident,
            "virtual_pages": total - resident,
            "ram_kb": resident * mmu.page_size / 1024,
            "ram_percent": resident / len(mmu.ram) * 100,
            "virtual_kb": virtual_bytes / 1024,
            "virtual_percent_of_ram": virtual_bytes / (len(mmu.ram) * mmu.page_size) * 100,
            "internal_fragmentation_kb": internal / 1024,
            "active_processes": active,
            "total_time": elapsed,
            "thrashing": thrashing,
            "thrashing_percent": thrashing / elapsed * 100 if elapsed else 0,
            "thrashing_warning": bool(elapsed and thrashing / elapsed > 0.5),
            "algorithm": name,
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as output:
            output.write(operations_to_text(self.operations))
