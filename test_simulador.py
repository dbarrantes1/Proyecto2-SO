import unittest

from simulador import Simulation, generate_operations, operations_to_text, parse_operations


class SimulatorTests(unittest.TestCase):
    def test_anexo_format_and_pointer_mapping(self):
        operations = parse_operations(
            "new(1,500)\nuse(1)\nnew(1,1000)\nuse(2)\n"
            "new(2,500)\nuse(3)\ndelete(1)\nkill(1)\n"
            "kill(2)\n"
        )
        self.assertEqual(operations[0].command, "new")
        self.assertEqual(operations[1].value, 1)
        self.assertEqual(len(parse_operations(operations_to_text(operations))), 9)

    def test_generation_is_reproducible_and_valid(self):
        first = generate_operations(42, 10, 500)
        second = generate_operations(42, 10, 500)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 500)
        self.assertEqual(parse_operations(operations_to_text(first)), first)

    def test_coordinated_simulation_and_metrics(self):
        operations = parse_operations(
            "new(1,5000)\nnew(2,5000)\nuse(1)\nuse(2)\n"
            "delete(1)\nkill(2)\n"
        )
        simulation = Simulation(operations, "FIFO")
        simulation.run()
        snapshot = simulation.snapshot()
        self.assertTrue(snapshot["finished"])
        self.assertEqual(snapshot["algorithms"]["OPT"]["total_time"], 24)
        self.assertEqual(snapshot["algorithms"]["FIFO"]["internal_fragmentation_kb"], 0)
        self.assertEqual(
            snapshot["algorithms"]["OPT"]["total_time"],
            snapshot["algorithms"]["FIFO"]["total_time"],
        )

    def test_pause_and_resume(self):
        simulation = Simulation(parse_operations("new(1,10)\n"), "LRU")
        simulation.pause()
        with self.assertRaises(RuntimeError):
            simulation.step()
        simulation.resume()
        simulation.step()
        self.assertTrue(simulation.snapshot()["finished"])


if __name__ == "__main__":
    unittest.main()
