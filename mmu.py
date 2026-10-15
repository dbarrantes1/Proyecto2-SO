from copy import deepcopy

class TemporaryAlgorithm:
    """Regla temporal: elige la primera página presente en RAM."""

    def on_load(self, page):
        pass

    def on_use(self, page):
        pass

    def on_evict(self, page):
        pass

    def on_delete(self, page):
        pass

    def choose_victim(self, ram, protected_pages):
        for page in ram:
            if page is not None and page not in protected_pages:
                return page

        raise MemoryError("No hay páginas disponibles para reemplazar")

class FIFO:
    """Expulsa la página que lleva más tiempo en RAM."""

    def __init__(self):
        self.order = []

    def on_load(self, page):
        if page not in self.order:
            self.order.append(page)

    def on_use(self, page):
        pass

    def on_evict(self, page):
        if page in self.order:
            self.order.remove(page)

    def on_delete(self, page):
        self.on_evict(page)

    def choose_victim(self, ram, protected_pages):
        for page in self.order:
            if page in ram and page not in protected_pages:
                return page

        raise MemoryError("FIFO: no hay víctimas disponibles")


class SecondChance:
    """Segunda oportunidad."""

    def __init__(self):
        self.order = []
        self.referenced = {}

    def on_load(self, page):
        if page not in self.order:
            self.order.append(page)
        self.referenced[page] = False

    def on_use(self, page):
        if page in self.referenced:
            self.referenced[page] = True

    def on_evict(self, page):
        if page in self.order:
            self.order.remove(page)
        self.referenced.pop(page, None)

    def on_delete(self, page):
        self.on_evict(page)

    def choose_victim(self, ram, protected_pages):
        # Se limita el recorrido para detectar si no hay
        # ninguna página elegible.
        for _ in range(2 * len(self.order) + 1):
            if not self.order:
                break

            page = self.order[0]

            if page not in ram:
                self.order.pop(0)
                continue

            if page in protected_pages:
                self.order.append(self.order.pop(0))
                continue

            if self.referenced.get(page, False):
                self.referenced[page] = False
                self.order.append(self.order.pop(0))
            else:
                return page

        raise MemoryError("SC: no hay víctimas disponibles")


class LRU:
    """Expulsa la página utilizada menos recientemente."""

    def __init__(self):
        self.clock = 0
        # Diccionario que almacena el último acceso de cada página.
        self.last_used = {}

    def on_load(self, page):
        self.clock += 1
        self.last_used[page] = self.clock

    def on_use(self, page):
        self.clock += 1
        self.last_used[page] = self.clock

    def on_evict(self, page):
        if page in self.last_used:
            del self.last_used[page]

    def on_delete(self, page):
        self.on_evict(page)

    def choose_victim(self, ram, protected_pages):
        candidates = []

        for page in ram:

            if page is None:
                continue

            if page in protected_pages:
                continue

            candidates.append(page)

        if len(candidates) == 0:
            raise MemoryError(
                "LRU: no hay víctimas disponibles"
            )

        victim = candidates[0]

        oldest_access = self.last_used.get(victim, 0)

        for page in candidates[1:]:

            last_access = self.last_used.get(page, 0)

            if last_access < oldest_access:
                victim = page
                oldest_access = last_access

        return victim


class LFU:
    """Expulsa la página con menos accesos."""

    def __init__(self):
        self.frequency = {}
        self.loaded_at = {}
        self.clock = 0

    def on_load(self, page):
        self.clock += 1
        self.frequency[page] = 1
        self.loaded_at[page] = self.clock

    def on_use(self, page):
        if page in self.frequency:
            self.frequency[page] += 1

    def on_evict(self, page):
        self.frequency.pop(page, None)
        self.loaded_at.pop(page, None)

    def on_delete(self, page):
        self.on_evict(page)

    
    def choose_victim(self, ram, protected_pages):
        candidates = []

        for page in ram:

            if page is None:
                continue

            if page in protected_pages:
                continue

            candidates.append(page)

        if len(candidates) == 0:
            raise MemoryError("LFU: no hay víctimas disponibles")

        victim = candidates[0]

        lowest_frequency = self.frequency.get(victim, 0)
        oldest_load = self.loaded_at.get(victim, 0)

        for page in candidates[1:]:

            current_frequency = self.frequency.get(page, 0)
            current_load = self.loaded_at.get(page, 0)

            if current_frequency < lowest_frequency:

                victim = page
                lowest_frequency = current_frequency
                oldest_load = current_load

            elif current_frequency == lowest_frequency:

                if current_load < oldest_load:
                    victim = page
                    oldest_load = current_load

        return victim


class OPT:
    """Algoritmo óptimo de reemplazo de páginas."""

    def __init__(self, references):
        self.references = references.copy()
        self.position = 0

    def on_load(self, page):
        pass

    def on_use(self, page):
        self.position += 1

    def on_evict(self, page):
        pass

    def on_delete(self, page):
        pass

    def choose_victim(self, ram, protected_pages):
        candidates = []

        for page in ram:

            if page is None:
                continue

            if page in protected_pages:
                continue

            candidates.append(page)

        if len(candidates) == 0:
            raise MemoryError("OPT: no hay víctimas disponibles")

        victim = candidates[0]

        next_use_victim = None

        for i in range(self.position + 1, len(self.references)):

            if self.references[i] == victim:
                next_use_victim = i
                break

        if next_use_victim is None:
            return victim

        for page in candidates[1:]:

            next_use_page = None

            for i in range(self.position + 1, len(self.references)):

                if self.references[i] == page:
                    next_use_page = i
                    break


            if next_use_page is None:
                return page


            if next_use_page > next_use_victim:
                victim = page
                next_use_victim = next_use_page

        return victim


class MMU:
    def __init__(self, algorithm):
        self.ram = [None] * 100
        self.page_size = 4096

        self.next_ptr = 1
        self.next_page = 1

        self.processes = {}
        self.ptrs = {}
        self.pages = {}

        self.algorithm = algorithm

        # Resultado del último new o use, para las estadísticas.
        self.last_access = {"hits": [], "faults": []}

    def new(self, pid: int, size: int) -> int:
        if type(size) is not int or size <= 0:
            raise ValueError("El tamaño debe ser un entero positivo")

        if type(pid) is not int:
            raise ValueError("El PID debe ser un entero")

        if pid in self.processes and self.processes[pid]["terminated"]:
            raise ValueError("El proceso ya terminó")

        num_pages = (size + self.page_size - 1) // self.page_size

        # Una asignación debe poder estar completa en RAM.
        if num_pages > len(self.ram):
            raise ValueError("La asignación supera la capacidad de RAM")

        if pid not in self.processes:
            self.processes[pid] = {
                "ptrs": [],
                "terminated": False
            }

        ptr = self.next_ptr
        self.next_ptr += 1

        self.ptrs[ptr] = {
            "pid": pid,
            "size": size,
            "pages": []
        }

        self.processes[pid]["ptrs"].append(ptr)

        # Primero crear todas las páginas de la asignación.
        for _ in range(num_pages):
            page = self.next_page
            self.next_page += 1

            self.pages[page] = {
                "ptr": ptr,
                "pid": pid,
                "in_ram": False,
                "frame": None
            }

            self.ptrs[ptr]["pages"].append(page)

        # Después cargarlas, protegiendo toda la asignación.
        protected_pages = frozenset(self.ptrs[ptr]["pages"])

        for page in self.ptrs[ptr]["pages"]:
            self.load_page(page, protected_pages)

        self.last_access = {
            "hits": [],
            "faults": self.ptrs[ptr]["pages"].copy()
        }

        return ptr

    def use(self, ptr: int):
        self._validate_ptr(ptr)

        pages_to_use = self.ptrs[ptr]["pages"]
        protected_pages = frozenset(pages_to_use)

        hits = []
        faults = []

        for page in pages_to_use:
            if self.pages[page]["in_ram"]:
                hits.append(page)
            else:
                self.load_page(page, protected_pages)
                faults.append(page)

            self.algorithm.on_use(page)

        self.last_access = {"hits": hits, "faults": faults}

        return {
            "hits": hits.copy(),
            "faults": faults.copy()
        }

    def delete(self, ptr: int):
        self._validate_ptr(ptr)

        for page in self.ptrs[ptr]["pages"]:
            if self.pages[page]["in_ram"]:
                frame = self.pages[page]["frame"]
                self.ram[frame] = None

            del self.pages[page]
            self.algorithm.on_delete(page)

        pid = self.ptrs[ptr]["pid"]
        self.processes[pid]["ptrs"].remove(ptr)
        del self.ptrs[ptr]
        self.last_access = {"hits": [], "faults": []}

    def kill(self, pid: int):
        if type(pid) is not int:
            raise ValueError("El PID debe ser un entero")

        if pid not in self.processes:
            raise ValueError("El proceso no existe")

        if self.processes[pid]["terminated"]:
            raise ValueError("El proceso ya terminó")

        while self.processes[pid]["ptrs"]:
            ptr = self.processes[pid]["ptrs"][0]
            self.delete(ptr)

        self.processes[pid]["terminated"] = True
        self.last_access = {"hits": [], "faults": []}

    def evict(self, page: int):
        self._validate_page(page)

        if not self.pages[page]["in_ram"]:
            raise ValueError("La página no está en RAM")

        frame = self.pages[page]["frame"]
        self.ram[frame] = None
        self.pages[page]["in_ram"] = False
        self.pages[page]["frame"] = None

        self.algorithm.on_evict(page)

    def load_page(self, page: int, protected_pages=frozenset()):
        self._validate_page(page)

        if self.pages[page]["in_ram"]:
            raise ValueError("La página ya está en RAM")

        if None not in self.ram:
            victim = self.choose_victim(protected_pages)
            self.evict(victim)

        frame = self.ram.index(None)
        self.ram[frame] = page
        self.pages[page]["in_ram"] = True
        self.pages[page]["frame"] = frame

        self.algorithm.on_load(page)


    def choose_victim(self, protected_pages=frozenset()) -> int:
        victim = self.algorithm.choose_victim(
            self.ram.copy(),
            frozenset(protected_pages)
        )

        self._validate_page(victim)

        if not self.pages[victim]["in_ram"]:
            raise ValueError("La página elegida no está en RAM")

        if victim in protected_pages:
            raise ValueError("El algoritmo eligió una página protegida")

        return victim

    def _validate_ptr(self, ptr):
        if type(ptr) is not int:
            raise ValueError("El puntero debe ser un entero")

        if ptr not in self.ptrs:
            raise ValueError("El puntero no existe")

    def _validate_page(self, page):
        if type(page) is not int:
            raise ValueError("La página debe ser un entero")

        if page not in self.pages:
            raise ValueError("La página no existe")

    def get_state(self):
        """Devuelve una copia del estado actual de esta MMU."""
        return deepcopy({
            "ram": self.ram,
            "page_size": self.page_size,
            "processes": self.processes,
            "ptrs": self.ptrs,
            "pages": self.pages,
            "next_ptr": self.next_ptr,
            "next_page": self.next_page,
            "last_access": self.last_access
        })


if __name__ == "__main__":
    mmu = MMU(TemporaryAlgorithm())

    ptr1 = mmu.new(7, 6000)          # Páginas 1 y 2.
    mmu.new(8, 4096 * 98)           # Completa la RAM.

    mmu.evict(2)
    mmu.new(9, 4096)                # Página 101.

    result = mmu.use(ptr1)

    print("Resultado:", result)
    print("Página 1:", mmu.pages[1])
    print("Página 2:", mmu.pages[2])
    print("Página 101:", mmu.pages[101])
    print("Marcos libres:", mmu.ram.count(None))

    assert result == {"hits": [1], "faults": [2]}
    assert all(
        mmu.pages[page]["in_ram"]
        for page in mmu.ptrs[ptr1]["pages"]
    )

    ptr4 = mmu.new(10, 6000)

    assert all(
        mmu.pages[page]["in_ram"]
        for page in mmu.ptrs[ptr4]["pages"]
    )

    print("Protección de páginas: pruebas correctas")