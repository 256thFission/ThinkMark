import argparse
import tracemalloc
from pathlib import Path
import time
import shutil
import os
import sys

# Add src to Python path to allow direct script execution
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from thinkmark.core.models import PipelineState, Document
from thinkmark.core.pipeline import markify_stage
from thinkmark.markify.adapter import process_document # Needed for markify_stage

# Ensure the mock for process_document used in tests is not active here.
# The actual process_document will be used.

def generate_dummy_docs(num_docs: int, state: PipelineState):
    """Generates N dummy HTML documents and adds them to the state."""
    print(f"Generating {num_docs} dummy documents...")
    for i in range(num_docs):
        doc_id = f"dummy_doc_{i}"
        doc = Document(
            id=doc_id,
            url=f"http://example.com/dummy/{i}",
            title=f"Dummy HTML Document {i}",
            content=f"<html><head><title>Dummy {i}</title></head><body><h1>Heading {i}</h1><p>This is dummy HTML content for document {i}.</p></body></html>",
            metadata={"type": "html"}
        )
        state.add_document(doc)
    print("Dummy documents generated.")

def run_benchmark(num_docs: int, output_base_dir: Path):
    """Runs the markify_stage benchmark and prints peak memory usage."""
    
    # Ensure a clean output directory for each run
    output_dir = output_base_dir / f"benchmark_run_{int(time.time())}"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state = PipelineState(site_url="http://example.com/benchmark", output_dir=output_dir)
    generate_dummy_docs(num_docs, state)

    print(f"Starting tracemalloc and running markify_stage for {num_docs} documents...")
    tracemalloc.start()
    
    start_time = time.time()
    markify_stage(state) # This is the function we're benchmarking
    end_time = time.time()
    
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"--- Benchmark Results for markify_stage ({num_docs} docs) ---")
    print(f"Execution Time: {end_time - start_time:.2f} seconds")
    print(f"Current memory usage: {current_mem / 1024**2:.2f} MB")
    print(f"Peak memory usage: {peak_mem / 1024**2:.2f} MB")
    print(f"Output written to: {output_dir}")

    # Optional: Clean up the generated output directory after benchmarking
    # shutil.rmtree(output_dir)
    # print(f"Cleaned up output directory: {output_dir}")
    return peak_mem

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark memory usage of markify_stage.")
    parser.add_argument(
        "--num-docs", 
        type=int, 
        default=1000, 
        help="Number of dummy documents to generate for the benchmark."
    )
    parser.add_argument(
        "--output-base-dir",
        type=Path,
        default=Path("/tmp/thinkmark_benchmark_output"),
        help="Base directory for benchmark output artifacts."
    )

    args = parser.parse_args()

    print("IMPORTANT:")
    print("To compare memory usage before and after changes, you need to:")
    print("1. Checkout the commit *before* the markify_stage in-place refactoring.")
    print("2. Run this script: python scripts/benchmark_markify_memory.py --num-docs N")
    print("3. Note the 'Peak memory usage'.")
    print("4. Checkout the commit *with* the markify_stage in-place refactoring (e.g., current commit).")
    print("5. Run this script again: python scripts/benchmark_markify_memory.py --num-docs N")
    print("6. Compare the peak memory usage values.")
    print("----------------------------------------------------------------------")

    run_benchmark(args.num_docs, args.output_base_dir)
