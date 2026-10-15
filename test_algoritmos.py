# -*- coding: utf-8 -*-

from mmu import FIFO, SecondChance, LRU, LFU, OPT


def probar_algoritmo(nombre, algoritmo, referencias, capacidad):
    """Ejecuta una secuencia de referencias y muestra las estadísticas."""

    ram = []
    hits = 0
    fallos = 0
    reemplazos = 0

    print("\n" + "=" * 65)
    print("ALGORITMO:", nombre)
    print("=" * 65)

    for indice, pagina_solicitada in enumerate(referencias):

        print(f"\nReferencia {indice + 1}: pagina {pagina_solicitada}")

        # OPT necesita conocer en qué posición de la secuencia estamos.
        # La implementación de OPT presentada anteriormente busca desde
        # position + 1; por eso, antes de decidir, position se fija en
        # indice - 1. Después on_use() lo incrementará.
        if isinstance(algoritmo, OPT):
            algoritmo.position = indice - 1

        if pagina_solicitada in ram:
            hits += 1
            print("Resultado: HIT (la página ya esta en RAM)")

            # Registrar el acceso a la página.
            algoritmo.on_use(pagina_solicitada)

        else:
            fallos += 1
            print("Resultado: FALLO DE PAGINA")

            if len(ram) >= capacidad:
                # En esta prueba no hay páginas protegidas.
                paginas_protegidas = frozenset()

                victima = algoritmo.choose_victim(
                    ram.copy(),
                    paginas_protegidas
                )

                print("Pagina expulsada:", victima)

                # Notificar al algoritmo y liberar el marco.
                algoritmo.on_evict(victima)
                ram.remove(victima)
                reemplazos += 1

            # Cargar la página solicitada.
            ram.append(pagina_solicitada)
            algoritmo.on_load(pagina_solicitada)

            # Registrar el acceso que ocasionó la referencia.
            algoritmo.on_use(pagina_solicitada)

        print("RAM actual:", ram)

    print("\n--- ESTADISTICAS FINALES ---")
    print("Algoritmo:", nombre)
    print("Total de referencias:", len(referencias))
    print("Hits:", hits)
    print("Fallos de pagina:", fallos)
    print("Reemplazos:", reemplazos)
    print("RAM final:", ram)

    # Comprobaciones generales.
    assert len(ram) <= capacidad, "La RAM supero su capacidad."
    assert hits + fallos == len(referencias), "Las estadisticas no coinciden."

    return {
        "algoritmo": nombre,
        "hits": hits,
        "fallos": fallos,
        "reemplazos": reemplazos,
        "ram_final": ram.copy(),
    }


def probar_proteccion(algoritmo, nombre):
    """Comprueba que el algoritmo no seleccione una página protegida."""

    # Las páginas 1, 2 y 3 están en RAM; la página 1 está protegida.
    ram = [1, 2, 3]
    protegidas = frozenset({1})

    # Preparar los metadatos de cada algoritmo para las tres páginas.
    for pagina in ram:
        algoritmo.on_load(pagina)

    # Dar prioridad a la página 2 en los algoritmos basados en historial,
    # cuando corresponda, para que la prueba sea determinista.
    if isinstance(algoritmo, LRU):
        algoritmo.last_used[1] = 3
        algoritmo.last_used[2] = 1
        algoritmo.last_used[3] = 2

    elif isinstance(algoritmo, LFU):
        algoritmo.frequency[1] = 1
        algoritmo.frequency[2] = 1
        algoritmo.frequency[3] = 2
        algoritmo.loaded_at[1] = 1
        algoritmo.loaded_at[2] = 2
        algoritmo.loaded_at[3] = 3

    elif isinstance(algoritmo, SecondChance):
        algoritmo.referenced[1] = False
        algoritmo.referenced[2] = False
        algoritmo.referenced[3] = False

    elif isinstance(algoritmo, OPT):
        algoritmo.references = [4, 5, 6]
        algoritmo.position = -1

    victima = algoritmo.choose_victim(ram.copy(), protegidas)

    assert victima not in protegidas, (
        f"{nombre} selecciono una pagina protegida: {victima}"
    )

    print(f"Proteccion de paginas: correcta para {nombre} (victima {victima})")


def main():
    # Secuencia común para todos los algoritmos.
    referencias = [1, 2, 3, 1, 4, 2, 5, 1, 2, 3, 4, 5]
    capacidad = 3

    # Crear una instancia nueva para cada algoritmo.
    configuraciones = [
        ("FIFO", lambda: FIFO()),
        ("Second Chance", lambda: SecondChance()),
        ("LRU", lambda: LRU()),
        ("LFU", lambda: LFU()),
        ("OPT", lambda: OPT(referencias)),
    ]

    resultados = []

    for nombre, crear_algoritmo in configuraciones:
        algoritmo = crear_algoritmo()

        resultado = probar_algoritmo(
            nombre,
            algoritmo,
            referencias,
            capacidad
        )
        resultados.append(resultado)

    print("\n" + "=" * 65)
    print("COMPARACION FINAL")
    print("=" * 65)
    print(f"{'Algoritmo':<18}{'Hits':<10}{'Fallos':<10}{'Reemplazos':<12}")

    for resultado in resultados:
        print(
            f"{resultado['algoritmo']:<18}"
            f"{resultado['hits']:<10}"
            f"{resultado['fallos']:<10}"
            f"{resultado['reemplazos']:<12}"
        )

    print("\n--- PRUEBAS DE PROTECCION ---")
    for nombre, crear_algoritmo in configuraciones:
        probar_proteccion(crear_algoritmo(), nombre)

    print("\nTodas las comprobaciones finalizaron correctamente.")


if __name__ == "__main__":
    main()
