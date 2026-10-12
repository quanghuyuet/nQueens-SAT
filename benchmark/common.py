"""Process isolation, timings, deadlines, and tables shared by benchmarks."""

import argparse
import math
import multiprocessing
from contextlib import contextmanager
from time import perf_counter

import psutil


BOARD_SIZES = (8, 16, 32, 64, 128, 256, 512)
TIMEOUT_SECONDS = 120.0


@contextmanager
def measure_time(connection, key):
    """Report elapsed seconds, including time spent in a failing stage."""
    started = perf_counter()
    try:
        yield
    finally:
        connection.send({key: perf_counter() - started})


def _worker_entry(worker, arguments, connection):
    try:
        worker(*arguments, connection)
    except Exception as error:
        connection.send({"status": "ERROR", "error": f"{type(error).__name__}: {error}"})
    finally:
        connection.close()


def _stop_process(process):
    """Stop a running worker and its native solver children on any platform."""
    if not process.is_alive():
        return
    children = []
    try:
        parent = psutil.Process(process.pid)
        # Freeze the worker so it cannot launch another solver during cleanup.
        parent.suspend()
        children = parent.children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
    finally:
        process.kill()
        process.join()
    _, alive = psutil.wait_procs(children, timeout=1)
    if alive:
        raise RuntimeError(f"Could not stop solver processes: {[p.pid for p in alive]}")


def run_process(worker, name, n, timeout=TIMEOUT_SECONDS, worker_args=()):
    """Run worker(name, n, *worker_args, connection) under one total deadline.

    Workers send small dictionaries as stages finish; models remain in the child.
    The deadline includes process startup, imports, construction, and solving.
    """
    positive_integer(n)
    positive_seconds(timeout)
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker_entry, args=(worker, (name, n, *worker_args), sender)
    )
    result = {
        "name": name, "n": n, "variables": None, "clauses": None,
        "build_seconds": None, "solve_seconds": None,
    }
    started = perf_counter()
    try:
        process.start()
        sender.close()
        deadline = started + timeout
        while "status" not in result:
            remaining = deadline - perf_counter()
            if remaining <= 0:
                result["status"] = "TIMEOUT"
                break
            if receiver.poll(remaining):
                try:
                    result.update(receiver.recv())
                except EOFError:
                    result.update(status="ERROR", error="Worker exited without a result")
    except Exception as error:
        result.update(status="ERROR", error=f"{type(error).__name__}: {error}")
    finally:
        result["total_seconds"] = perf_counter() - started
        if process.pid is not None:
            process.join(timeout=0 if result.get("status") == "TIMEOUT" else 0.1)
            try:
                _stop_process(process)
            except Exception as error:
                result.update(status="ERROR", error=f"Process cleanup failed: {error}")
        process.close()
        sender.close()
        receiver.close()
    return result


def positive_integer(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def add_run_arguments(parser):
    parser.add_argument("--sizes", nargs="+", type=positive_integer, default=BOARD_SIZES)
    parser.add_argument("--timeout", type=positive_seconds, default=TIMEOUT_SECONDS,
                        help="total wall-clock limit per test (default: 120 seconds)")


def _number(value):
    return "--" if value is None else f"{value:,}"


def _seconds(value):
    return "--" if value is None else f"{value:.4f}"


def print_header(title, timeout, include_counts=False):
    print(f"{title} | timeout: {timeout:g} s/test", flush=True)
    print("Build = model/CNF construction; Solve = solve API call (including presolve).")
    print("Total includes startup, imports, solver setup, CNF loading and communication.")
    if not include_counts:
        print("CP solve includes model serialization and CP Optimizer process startup.")
    print("-- = stage not reached/unfinished; times are in seconds.\n", flush=True)
    counts = f" {'Vars':>9} {'Clauses':>11}" if include_counts else ""
    header = (f"{'Encoding' if include_counts else 'Solver':<25} {'N':>5}{counts} "
              f"{'Build':>9} {'Solve':>9} {'Total':>9} {'Status':<7}")
    print(header)
    print("-" * len(header), flush=True)


def print_result(result, include_counts=False):
    counts = (f" {_number(result['variables']):>9} {_number(result['clauses']):>11}"
              if include_counts else "")
    print(
        f"{result['name']:<25} {result['n']:>5}{counts} "
        f"{_seconds(result['build_seconds']):>9} "
        f"{_seconds(result['solve_seconds']):>9} "
        f"{_seconds(result['total_seconds']):>9} {result['status']:<7}",
        flush=True,
    )
    if "error" in result:
        print(f"  {result['error']}", flush=True)
