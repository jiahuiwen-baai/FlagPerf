# Copyright (c) 2024 BAAI. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import time
from loguru import logger
from triton.testing import do_bench as kernel_bench
import os
import subprocess
sys.path.append("/home/jhw/jiahuiwen/FlagPerf/operation/")
from container_main import get_performance_log


# 算子正确性入口
def do_correctness(operation):
    flaggems_dir = os.getenv("FLAGGEMS_WORK_DIR", "/")
    gems_repo = subprocess.check_output(
        ["find", flaggems_dir, "-type", "d", "-name", "FlagGems"], text=True).strip()
    p = subprocess.Popen(
        f"cd {os.path.join(gems_repo, 'tests')} && python3 test_named_ops.py --name {operation} --device cpu ",
        shell=True
        )
    p.wait()

    return p.returncode

# 算子性能入口
def do_performance(mode, warmup):
    logger.add(save_log_path + "jhw_test.log")
    logger.info("save_log_path=========")
    logger.info(save_log_path)
    logger.info("canshu=========")
    logger.info(mode)
    logger.info(warmup)
    flaggems_dir = os.getenv("FLAGGEMS_WORK_DIR", "/")
    gems_repo = subprocess.check_output(
        ["find", flaggems_dir, "-type", "d", "-name", "FlagGems"], text=True).strip()
    p = subprocess.Popen(
        # f"cd {os.path.join(gems_repo, 'benchmark')} && pytest --level core --mode {mode} --warmup {warmup} --record log ",
        # f"cd {os.path.join(gems_repo, 'benchmark')} && pytest -m mm --level core --mode {mode} --warmup {warmup} --record log -s",
        # f"cd {os.path.join(gems_repo, 'benchmark')} && pytest test_blas_perf.py --level  core --mode {mode} --warmup {warmup} --record log",
        f"cd {os.path.join(gems_repo, 'benchmark')} && pytest test_blas_perf.py --level core --mode {mode} --warmup {warmup} --record log",
        shell=True
    )
    p.wait()
    logger.info("gems_repo=========")
    logger.info(gems_repo)
    # log_dir = os.path.join(gems_repo, "benchmark", "result--level_core--record_log")
    log_dir = os.path.join(gems_repo, "benchmark",
                           "result_test_blas_perf--level_core--mode_cpu--warmup_0--record_log.log")
    # log_dir = os.path.join(gems_repo, "benchmark", "result-m_mm--level_core--mode_cpu--warmup_1000--record_log-s.log")
    logger.info("log_dir=========")
    logger.info(log_dir)
    save_log_path = get_performance_log()
    save_path = save_log_path + "result.log.txt"
    with open(log_dir, "r", encoding="utf-8") as file_r, open(save_path, "w", encoding="utf-8") as file_w:
        for line in file_r:
            logger.info("result.log.txt print ok")
            file_w.write(line + '\n')
    return p.returncode


grad_outputs = None

def do(exec_func, exec_args, bp=False):
    global grad_outputs
    if bp:
        import torch
        _tensor = exec_func(*exec_args).sum()
        if grad_outputs is None:
            grad_outputs = torch.zeros_like(_tensor)
        inputs = list(filter(lambda x: x.requires_grad, [*exec_args]))
        _grad = torch.autograd.grad(outputs=_tensor, inputs=inputs, grad_outputs=grad_outputs)
    else:
        _tensor = exec_func(*exec_args)


def do_test(exec_func, exec_args, sync_func, config, case_config, bp=False):
    sync_func(config.vendor)
    start_latency_nowarm = time.perf_counter_ns()
    _tensor = exec_func(*exec_args)

    sync_func(config.vendor)
    latency_nowarm = time.perf_counter_ns() - start_latency_nowarm

    for _ in range(case_config.WARMUP):
        do(exec_func, exec_args, bp)

    sync_func(config.vendor)
    start_latency_warm = time.perf_counter_ns()
    _tensor = exec_func(*exec_args)

    sync_func(config.vendor)
    latency_warm = time.perf_counter_ns() - start_latency_warm

    start_time = time.perf_counter()
    for _ in range(case_config.ITERS):
        do(exec_func, exec_args, bp)

    sync_func(config.vendor)
    end_time = time.perf_counter()

    cputime_raw = end_time - start_time

    kerneltime_raw = kernel_bench(lambda: do(exec_func, exec_args, bp),
                                  warmup=case_config.KERNELWARMUP,
                                  rep=case_config.KERNELITERS,
                                  return_mode="median")
    cputime = cputime_raw / case_config.ITERS
    kerneltime = kerneltime_raw / 1000.0  # ms to s
    return round(latency_nowarm / 1000.0, 2), round(latency_warm / 1000.0,
                                                    2), cputime, kerneltime


def cal_perf(cputime, kerneltime, op2flops, spectflops, bp=False):
    spectflops = float(spectflops)
    ctus = round(cputime * 1E6, 2)
    ktus = round(kerneltime * 1E6, 2)

    cps = 1.0 / cputime
    kps = 1.0 / kerneltime

    cflops = op2flops(cps) * (3.0 if bp else 1.0)
    kflops = op2flops(kps) * (3.0 if bp else 1.0)
    ctflops = round(cflops / 1E12, 2)
    ktflops = round(kflops / 1E12, 2)

    cfu = round(100.0 * cflops / 1E12 / spectflops, 2)
    kfu = round(100.0 * kflops / 1E12 / spectflops, 2)

    return ctus, ktus, cps, kps, ctflops, ktflops, cfu, kfu


def print_result(config, casename, ct, kt, cps, kps, ctflops, ktflops, cfu,
                 kfu, correctness, lnm, lm):
    print(r"[FlagPerf Result]Operation {} in {} at {}:".format(
        casename, config.oplib, config.dataformat))
    print(r"[FlagPerf Result]FLOPS utilization: cputime={}%, kerneltime={}%".
          format(cfu, kfu))
    print(
        r"[FlagPerf Result]cputime={} us, throughput={} op/s, equals to {} TFLOPS"
        .format(ct, cps, ctflops))
    print(
        r"[FlagPerf Result]kerneltime={} us, throughput={} op/s, equals to {} TFLOPS"
        .format(kt, kps, ktflops))
    print(r"[FlagPerf Result]Correctness with CPU golden Reference: {}".format(
        correctness))
    print(
        r"[FlagPerf Result]First time latency: no warmup={} us, warmup={} us".
        format(lnm, lm))
