"""Process isolation, timeouts, memory limits and command-line options shared by benchmarks."""

import argparse
import math
import multiprocessing
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter

import psutil


BOARD_SIZES = (8, 16, 32, 64, 128, 256, 512)
TIMEOUT_SECONDS = 120.0
DEFAULT_THREADS = 1
POLL_SECONDS = 0.05  # how often the parent samples memory while waiting


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
    except MemoryError:
        connection.send({"status": "MEMOUT", "error": "MemoryError inside the worker"})
    except Exception as error:
        connection.send({"status": "ERROR", "error": f"{type(error).__name__}: {error}"})
    finally:
        connection.close()


def _tree_rss_mb(process):
    """Resident memory (MB) of the worker plus its native solver children."""
    try:
        parent = psutil.Process(process.pid)
        processes = [parent] + parent.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
    total = 0
    for item in processes:
        try:
            total += item.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total / (1024 * 1024)


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


def run_process(worker, name, n, timeout=TIMEOUT_SECONDS, worker_args=(),
                memory_limit_mb=None):
    """Run worker(name, n, *worker_args, connection) under one total deadline.

    Workers send small dictionaries as stages finish; models remain in the child.
    The deadline includes process startup, imports, construction, and solving.
    The parent samples the worker's memory every POLL_SECONDS. If it exceeds
    memory_limit_mb the test is stopped with status MEMOUT. A worker killed by
    SIGKILL (the Linux out-of-memory killer) is also reported as MEMOUT.
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
        "build_seconds": None, "solve_seconds": None, "peak_memory_mb": None,
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
            if receiver.poll(min(remaining, POLL_SECONDS)):
                try:
                    result.update(receiver.recv())
                except EOFError:
                    process.join(timeout=1)
                    if process.exitcode == -9:
                        result.update(
                            status="MEMOUT",
                            error="Worker was killed (SIGKILL), probably out of memory")
                    else:
                        result.update(
                            status="ERROR",
                            error=f"Worker exited without a result (exit code {process.exitcode})")
            rss = _tree_rss_mb(process)
            if rss is not None:
                peak = result["peak_memory_mb"]
                result["peak_memory_mb"] = rss if peak is None else max(peak, rss)
                if (memory_limit_mb is not None and rss > memory_limit_mb
                        and "status" not in result):
                    result.update(
                        status="MEMOUT",
                        error=f"Memory limit of {memory_limit_mb:g} MB exceeded")
    except Exception as error:
        result.update(status="ERROR", error=f"{type(error).__name__}: {error}")
    finally:
        result["total_seconds"] = perf_counter() - started
        if process.pid is not None:
            stopping = result.get("status") in ("TIMEOUT", "MEMOUT")
            process.join(timeout=0 if stopping else 0.1)
            try:
                _stop_process(process)
            except Exception as error:
                result.update(status="ERROR", error=f"Process cleanup failed: {error}")
        process.close()
        sender.close()
        receiver.close()
    return result


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

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


def add_run_arguments(parser, threads=True):
    parser.add_argument("--sizes", nargs="+", type=positive_integer, default=BOARD_SIZES)
    parser.add_argument("--timeout", type=positive_seconds, default=TIMEOUT_SECONDS,
                        help="total wall-clock limit per test (default: 120 seconds)")
    parser.add_argument("--repeats", type=positive_integer, default=1,
                        help="runs per (solver, N); a median table is printed when > 1")
    parser.add_argument("--memory-limit-mb", type=positive_seconds, default=None,
                        help="stop a test with status MEMOUT above this memory "
                             "(worker + child processes); default: no limit")
    parser.add_argument("--output", type=Path, default=None,
                        help="CSV file to append results to "
                             "(default: results/<benchmark>_<timestamp>.csv)")
    if threads:
        parser.add_argument("--threads", type=positive_integer, default=DEFAULT_THREADS,
                            help="threads for CP-SAT, Gurobi, CPLEX MIP and CPLEX CP "
                                 "(default: 1; the SAT solver is single-threaded)")
