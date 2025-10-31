"""
Performance Benchmark Script
Tests API performance with different configurations

Usage:
    python benchmark_performance.py --pdf sample.pdf
    python benchmark_performance.py --pdf sample.pdf --batch-mode --test-count 250
"""

import asyncio
import time
import json
import argparse
import aiohttp
from pathlib import Path


async def benchmark_endpoint(
    pdf_path: str,
    endpoint_url: str = "http://localhost:8080/generate-ui-tests",
    batch_mode: bool = False,
    test_count: int = 50,
    gdpr_mode: bool = True
):
    """
    Benchmark a single API call

    Args:
        pdf_path: Path to PDF file
        endpoint_url: API endpoint URL
        batch_mode: Enable batch generation
        test_count: Target test count (batch mode only)
        gdpr_mode: Enable GDPR masking

    Returns:
        Dictionary with timing results
    """
    print(f"\n{'='*80}")
    print(f"🔬 BENCHMARK: {'Batch Mode' if batch_mode else 'Normal Mode'}")
    print(f"{'='*80}")
    print(f"   PDF: {pdf_path}")
    print(f"   Batch Mode: {batch_mode}")
    if batch_mode:
        print(f"   Target Tests: {test_count}")
    print(f"   GDPR Mode: {gdpr_mode}")

    # Prepare request
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Build request params
    params = {
        "gdpr_mode": str(gdpr_mode).lower(),
        "batch_mode": str(batch_mode).lower()
    }
    if batch_mode:
        params["test_count"] = test_count

    # Measure total time
    start_time = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            # Prepare multipart form data
            with open(pdf_path, 'rb') as f:
                form = aiohttp.FormData()
                form.add_field('file', f, filename=pdf_file.name, content_type='application/pdf')

                print(f"\n📤 Sending request to {endpoint_url}...")
                async with session.post(endpoint_url, data=form, params=params, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API returned {response.status}: {error_text}")

                    result = await response.json()

        end_time = time.time()
        total_time = end_time - start_time

        # Extract metrics from response
        test_suite = result.get("test_suite", {})
        statistics = test_suite.get("statistics", {})
        total_tests = statistics.get("total_tests", 0)

        pipeline_metadata = result.get("pipeline_metadata", {})

        # Calculate derived metrics
        tests_per_second = total_tests / total_time if total_time > 0 else 0
        seconds_per_test = total_time / total_tests if total_tests > 0 else 0

        print(f"\n✅ BENCHMARK RESULTS:")
        print(f"{'='*80}")
        print(f"⏱️  Total Time: {total_time:.2f} seconds")
        print(f"🧪 Tests Generated: {total_tests}")
        print(f"⚡ Tests/Second: {tests_per_second:.2f}")
        print(f"🕐 Seconds/Test: {seconds_per_test:.2f}")
        print(f"{'='*80}")

        # Pipeline stage breakdown
        print(f"\n📊 PIPELINE BREAKDOWN:")
        for stage_name, stage_data in pipeline_metadata.items():
            if isinstance(stage_data, dict) and "status" in stage_data:
                print(f"   {stage_name}: {stage_data.get('status', 'unknown')}")

        return {
            "mode": "batch" if batch_mode else "normal",
            "total_time": round(total_time, 2),
            "total_tests": total_tests,
            "tests_per_second": round(tests_per_second, 2),
            "seconds_per_test": round(seconds_per_test, 2),
            "target_tests": test_count if batch_mode else "N/A",
            "pipeline_metadata": pipeline_metadata,
            "status": "success"
        }

    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time

        print(f"\n❌ BENCHMARK FAILED:")
        print(f"   Error: {str(e)}")
        print(f"   Time elapsed: {total_time:.2f} seconds")

        return {
            "mode": "batch" if batch_mode else "normal",
            "total_time": round(total_time, 2),
            "error": str(e),
            "status": "failed"
        }


async def run_comparison_benchmark(pdf_path: str, endpoint_url: str = "http://localhost:8080/generate-ui-tests"):
    """
    Run comparison benchmark: Normal vs Batch mode

    Args:
        pdf_path: Path to PDF file
        endpoint_url: API endpoint URL
    """
    print(f"\n{'='*80}")
    print(f"🚀 RUNNING COMPARISON BENCHMARK")
    print(f"{'='*80}")

    results = []

    # Test 1: Normal mode (baseline)
    print(f"\n\n📝 TEST 1: Normal Mode (Baseline)")
    normal_result = await benchmark_endpoint(
        pdf_path=pdf_path,
        endpoint_url=endpoint_url,
        batch_mode=False,
        gdpr_mode=True
    )
    results.append(normal_result)

    # Wait between tests
    print(f"\n⏸️  Waiting 5 seconds before next test...")
    await asyncio.sleep(5)

    # Test 2: Batch mode with 50 tests
    print(f"\n\n🚀 TEST 2: Batch Mode (50 tests)")
    batch_50_result = await benchmark_endpoint(
        pdf_path=pdf_path,
        endpoint_url=endpoint_url,
        batch_mode=True,
        test_count=50,
        gdpr_mode=True
    )
    results.append(batch_50_result)

    # Wait between tests
    print(f"\n⏸️  Waiting 5 seconds before next test...")
    await asyncio.sleep(5)

    # Test 3: Batch mode with 250 tests
    print(f"\n\n🚀 TEST 3: Batch Mode (250 tests)")
    batch_250_result = await benchmark_endpoint(
        pdf_path=pdf_path,
        endpoint_url=endpoint_url,
        batch_mode=True,
        test_count=250,
        gdpr_mode=True
    )
    results.append(batch_250_result)

    # Print comparison summary
    print(f"\n\n{'='*80}")
    print(f"📊 BENCHMARK COMPARISON SUMMARY")
    print(f"{'='*80}")

    print(f"\n{'Mode':<20} {'Tests':<10} {'Time (s)':<12} {'Tests/s':<12} {'s/Test':<10} {'Status':<10}")
    print(f"{'-'*80}")

    for result in results:
        if result.get("status") == "success":
            print(f"{result['mode']:<20} {result['total_tests']:<10} {result['total_time']:<12} {result['tests_per_second']:<12} {result['seconds_per_test']:<10} {result['status']:<10}")
        else:
            print(f"{result['mode']:<20} {'N/A':<10} {result['total_time']:<12} {'N/A':<12} {'N/A':<10} {result['status']:<10}")

    # Calculate speedup
    if results[0].get("status") == "success" and results[2].get("status") == "success":
        normal_time_per_test = results[0]["seconds_per_test"]
        batch_time_per_test = results[2]["seconds_per_test"]
        speedup = normal_time_per_test / batch_time_per_test if batch_time_per_test > 0 else 0

        print(f"\n{'='*80}")
        print(f"⚡ PERFORMANCE IMPROVEMENT:")
        print(f"   Normal mode: {normal_time_per_test:.2f} seconds/test")
        print(f"   Batch mode (250): {batch_time_per_test:.2f} seconds/test")
        print(f"   Speedup: {speedup:.2f}x faster per test")
        print(f"{'='*80}")

    # Save results to JSON
    output_file = "benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {output_file}")

    return results


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Benchmark PDF processing API performance")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--endpoint", default="http://localhost:8080/generate-ui-tests", help="API endpoint URL")
    parser.add_argument("--batch-mode", action="store_true", help="Enable batch mode")
    parser.add_argument("--test-count", type=int, default=50, help="Target test count (batch mode only)")
    parser.add_argument("--comparison", action="store_true", help="Run full comparison benchmark (normal vs batch)")

    args = parser.parse_args()

    if args.comparison:
        # Run full comparison
        await run_comparison_benchmark(args.pdf, args.endpoint)
    else:
        # Run single benchmark
        await benchmark_endpoint(
            pdf_path=args.pdf,
            endpoint_url=args.endpoint,
            batch_mode=args.batch_mode,
            test_count=args.test_count
        )


if __name__ == "__main__":
    asyncio.run(main())
