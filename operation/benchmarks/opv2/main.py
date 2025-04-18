 # Copyright (c) 2024 BAAI. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import torch
import os
import time
from argparse import ArgumentParser, Namespace
import yaml
import sys
import subprocess

sys.path.append("..")
from drivers.utils import *
from drivers.calculate import *
from drivers.parse_log import *


def parse_args():
    parser = ArgumentParser(description=" ")

    parser.add_argument("--vendor",
                        type=str,
                        required=True,
                        help="vendor name like nvidia")
    parser.add_argument("--case_name",
                        type=str,
                        required=True,
                        help="op name like mm")
    parser.add_argument("--spectflops",
                        type=str,
                        required=True,
                        help="spectflops of current dataformat")

    parser.add_argument("--dataformat",
                        type=str,
                        required=True,
                        help="like FP32,FP16")

    parser.add_argument("--oplib",
                        type=str,
                        required=True,
                        help="impl like pytorch/flaggems/cpp")

    parser.add_argument("--chip",
                        type=str,
                        required=True,
                        help="chip like A100_40_SXM")

    parser.add_argument("--mode",
                        type=str,
                        required=True,
                        help="mode like cpu")

    parser.add_argument("--warmup",
                        type=str,
                        required=True,
                        help="warmup")

    parser.add_argument("--log_dir",
                        type=str,
                        required=True,
                        help="abs log dir")

    parser.add_argument("--result_log_path",
                        type=str,
                        required=True,
                        help="result log path for FlagPerf/operation/result")

    args, unknown_args = parser.parse_known_args()
    args.unknown_args = unknown_args
    return args


def main(config):
    correctness = do_correctness(config.case_name)
    correctness = correctness == 0

    # test operation performance
    performance = do_performance(config.mode, config.warmup, config.log_dir)
    performance = performance == 0
    parse_log_file(config.spectflops, config.mode, config.warmup, config.log_dir, config.result_log_path)

    # dtype = {
    #     "FP32": torch.float32,
    #     "FP16": torch.float16,
    #     "BF16": torch.bfloat16,
    #     "INT32": torch.int32,
    #     "INT16": torch.int16,
    #     "BOOL": torch.bool
    #     }
    # set_ieee_float32(config.vendor)
    #
    #
    # m = case_config.Melements
    #
    #
    # a = torch.randn(m, 1024, 1024, dtype=dtype[config.dataformat]).to(0)
    #
    # latency_nowarm, latency_warm, cputime, kerneltime = do_test(
    #     torch.abs, (a, ), host_device_sync, config, case_config)
    #
    # op2flops = lambda x: x * m * 1024 * 1024
    #
    # perf_result = cal_perf(cputime, kerneltime, op2flops,
    #                        config.spectflops)
    # print_result(config, config.case_name, *perf_result, correctness,
    #              latency_nowarm, latency_warm)

if __name__ == "__main__":
    config = parse_args()
    # with open("case_config.yaml", "r") as file:
    #     case_config = yaml.safe_load(file)
    # adapt_torch(config.vendor)
    # with open(os.path.join(config.vendor, config.chip, "case_config.yaml"),
    #           "r") as file:
    #     case_config_vendor = yaml.safe_load(file)
    # case_config.update(case_config_vendor)
    # case_config = Namespace(**case_config)

    if config.oplib == "flaggems":
        import flag_gems
        flag_gems.enable()
        print("Using flaggems")
    else:
        print("Using nativetorch")
    main(config)