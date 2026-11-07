# C++ HPC Performance Engineering

面向现代 C++ 高性能计算的 Codex skill。它把性能工作组织成一条可复现的工程链路：定义性能契约、冻结证据身份、建立正确性基线、定位瓶颈、形成可证伪假设、单变量实验、验证全部门槛，再报告可复现结果。

这不是一份“编译器参数大全”，也不会把微基准中的偶然提升包装成生产加速。所有优化结论都必须关联目标工作负载、实际硬件、已加载二进制、统计不确定性、数值正确性和资源约束。

## 模型适配

Skill 保持模型无关，并依据 [GPT-6 Astra 官方提示指南](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra) 调整执行方式：继承同一范围内已有授权，按静态评审、文档或工具修复、性能优化与正式验收选择所需证据。核验强度取决于变更风险；相关检查通过后，只因新变更、失败或未解决疑点扩大验证。正式性能协议中的重复测量仍然必需。

独立检查可按收益并行或委派；正式 benchmark 和 profiler 必须隔离共享测量资源。最终答复给出结论、关键证据和限制，完整实验记录放入项目产物。自动检查验证打包结构、引用和工具行为，不能证明模型理解了指令；行为判断需要真实任务试用，见 [Astra 试用记录](evaluation/astra-2026-09-08.md)。

## 能力概览

- **测量与实验**：冷/热路径、重复运行、P95/P99、随机交错配对 A/B、bootstrap 区间、回归门槛和候选回滚。
- **CPU 与内存层次**：AoS、SoA、AoSoA、内存对齐、Cache Line、TLB、NUMA、Blocking/Tiling、预取、流式存储和工作集治理。
- **向量化与并行**：SIMD、编译器向量化报告、OpenMP、MPI、线程绑定、伪共享和负载均衡。
- **领域库集成**：oneTBB 并发所有权、oneDAL 分析契约、Intel IPP 领域原语、数据边界与运行时分派验证。
- **GPU 与异构计算**：CUDA、HIP、SYCL、分层 Tiling、软件流水线、融合、占用率、传输、持久化内核和自动调优。
- **稀疏与矩阵自由计算**：CSR/CSC/BSR/ELL、格式转换摊销、Inspector-Executor、Partial Assembly、Matrix-Free 和求解总时间。
- **表达式与数据管线**：表达式模板惰性求值、延迟/异步执行、懒加载、有界流式处理、JIT/计划缓存和生成代码身份。
- **数值与可复现性**：误差预算、ULP/相对/绝对误差、归约顺序、混合精度、确定性模式和数值回归测试。
- **Linux CPU 诊断**：按问题选择 `perf stat`、采样、源码标注、`perf c2c` 或扩展性对比，并输出结构化热点证据。
- **性能模式卡片**：从 `from-source`、`from-profile`、`new-code` 三类上下文检索模式，同时记录反证、正确性风险和验证方法。

## 设计来源

Skill 提炼的是可迁移策略，而不是要求项目引入特定依赖。

| 领域 | 参考项目 | 提炼的策略 |
| --- | --- | --- |
| 表达式与张量 | Eigen、NVIDIA MatX | 选择性融合、别名契约、显式执行器、异步生命周期、计划缓存 |
| 稠密与稀疏代数 | Intel oneMKL、Ginkgo、Kokkos Kernels | 调优内核优先、Inspector-Executor、Executor/Memory Space、可复用稀疏状态 |
| 稀疏张量编译 | TACO | 分离代数表达式、存储格式和执行调度 |
| 生成式 stencil | waLBerla、pystencils | 从数值语义生成 CPU/GPU 内核，显式布局、向量宽度、Blocking 和通信打包 |
| 高阶有限元 | libCEED、MFEM | 算子分解、Partial Assembly、Matrix-Free、后端解耦 |
| 并行执行与通信 | Kokkos、RAJA、MPI | 策略与算法分离、层次并行、并发预算、持久通信 |
| 任务、分析与领域原语 | oneTBB、oneDAL、Intel IPP | 调度所有权、分析语义、数据表示、领域内核、运行时 ISA 分派 |
| 内核结构 | BLIS、FFTW、CUTLASS、AMReX | 多级分块、Packing、规划缓存、软件流水线、内存池 |
| Linux CPU 诊断 | intel/intel-performance-skills | 问题驱动的 `perf` 流程、cache-line 归因和上下文模式卡片 |

详细策略按需加载：

- [库与框架策略](references/library-strategies.md)
- [稀疏、结构化与矩阵自由计算](references/sparse-matrix-free.md)
- [表达式、代码生成与流式处理](references/expression-codegen-streaming.md)
- [CPU 与内存优化](references/cpu-memory.md)
- [SIMD 与向量化](references/simd-vectorization.md)
- [GPU 优化](references/gpu.md)
- [Linux perf 诊断流程](references/linux-perf-workflows.md)
- [性能模式卡片](references/performance-patterns.md)

`intel/intel-performance-skills` 是 MIT 许可的 optional reference；本仓库只
独立提炼可迁移的方法，并增加跨厂商、正确性、权限和证据等级约束。它不是
安装或运行本 skill 所需的依赖（no runtime dependency）。

`uxlfoundation/skills` 是 optional research reference。本仓库选择性吸收其
oneTBB 工作负载分类和 oneDAL 语义验证思路；截至 2026-09-02 的复核，其
对应条目标记为 `incubating`。状态、具体 API、设备和算法支持应在使用时
重查上游及项目官方文档。它同样不是安装或运行本 skill 所需的依赖
（no runtime dependency）。

## 安装

将仓库克隆到 Codex 的个人 skills 目录：

~~~powershell
git clone https://github.com/ansleliu/cpp-hpc-skill.git "$HOME\.codex\skills\cpp-hpc-performance-engineering"
~~~

Linux/macOS：

~~~bash
git clone \
  https://github.com/ansleliu/cpp-hpc-skill.git \
  ~/.codex/skills/cpp-hpc-performance-engineering
~~~

重新启动 Codex 或开始一个新任务，使 skill 元数据重新载入。

## 双远端维护

维护副本的 `main` 跟踪私有 GitLab 的 `origin/main`，`codex/public-main`
跟踪公开 GitHub 的 `github/main`。公开历史从审阅后的发布快照开始，两个
分支的文件内容应保持一致，提交哈希可以不同。

在 `main` 完成变更后，将审阅过的公开提交按顺序 `cherry-pick` 到
`codex/public-main`。不要将私有分支合并到公开分支，也不要直接向 GitHub
推送私有 `main`。用 `git diff --exit-code main codex/public-main` 核对内容，
再分别推送 `git push origin main` 和 `git push github codex/public-main:main`。
配置了本地 `git push-both` 的维护副本可用它检查内容并顺序推送两个远端；
两次推送分别成功后再确认两端已同步。

## 使用

可显式调用：

~~~text
使用 $cpp-hpc-performance-engineering 分析这个 C++ SpMV 内核的内存瓶颈，
给出可复现的基准方案，并比较 CSR、BSR 和矩阵自由实现。
~~~

也可通过问题上下文自动触发，例如：

- “这个 AoS 循环为什么没有被 AVX-512 向量化？”
- “验证 OpenMP + oneMKL 是否发生线程过度订阅。”
- “比较 Eigen 表达式融合与显式临时量的端到端性能。”
- “为 CUDA kernel 建立 Roofline、占用率和流水线实验。”
- “评估 libCEED/MFEM Partial Assembly 的内存与求解时间。”

## 工具

仓库提供可独立运行的辅助脚本：

| 脚本 | 用途 |
| --- | --- |
| **collect_system_info.py** | 收集系统、亲和性、编译器、GPU 和 profiler 信息 |
| **run_benchmark.py** | 重复运行单个候选并保存可复现元数据 |
| **run_ab_benchmark.py** | 随机交错的配对 A/B 实验与 bootstrap 区间 |
| **compare_benchmarks.py** | 比较已保存结果及其统计不确定性 |
| **perf_stat.sh** | 探测并记录可用 Linux perf stat 计数器 |
| **check_vectorization.sh** | 生成 GCC、Clang、Intel 或 MSVC 向量化报告 |

向量化脚本不带命令时打印各编译器族的推荐参数；无法识别编译器名称时用
`--compiler` 明确选择。系统采集 shell 入口会先验证 Python 能否启动，
避免把不可用的 `python3` 占位命令当成可用解释器。

基准运行器将显式相对程序路径及 `PATH` 中的相对目录按 `--cwd` 解析，身份
记录使用相同路径。哈希采集受锁或权限限制时记录 `identity_error` 并保留
原始观测，同时提示身份尚未验证。启动失败会写入 JSON 的 `launch_error`，返回 126（无法执行）
或 127（未找到）；`--allow-failure` 可继续收集失败记录，因此仍须检查成功
样本数量。加速比比较要求两侧样本均为有限正数，零值、负值和非有限值不会
被当作有效比较；A/B 没有完整有效样本对时返回 65，并保留原始观测。

程序路径保留符号链接，避免启动时切换到虚拟环境之外的解释器。输出按
UTF-8 解码，不合法字节使用替换字符保留；正则捕获组为空时记录指标错误。
若已配置内部指标但样本缺失，比较工具会报错；需要比较进程耗时时显式指定
`--field elapsed_seconds`。计时选项要求有限值，超时必须大于零。

Shell 工具无法保存必要报告时返回 74；如果编译器或 perf 本身已经失败，
则优先保留其退出码。`perf_stat.sh` 找不到 perf 时返回 127，没有可用事件时
返回 69，这两种情况均不会运行被测命令。无 Python 的最小采集路径也会检查
写入错误，并转义 JSON 中的文件路径。

使用前查看参数：

~~~powershell
python scripts/run_benchmark.py --help
python scripts/run_ab_benchmark.py --help
~~~

优先使用能测量真实内核的项目原生 benchmark；这些脚本用于补足证据记录和通用实验编排。

## 仓库结构

~~~text
.
|-- SKILL.md                  # 触发条件、核心约束与端到端工作流
|-- agents/openai.yaml        # Codex UI 元数据
|-- references/               # 按主题渐进加载的性能工程参考
|-- scripts/                  # 基准、A/B、系统信息和编译器报告工具
|-- evaluation/               # 有适用范围和局限说明的行为试用记录
|-- .gitignore
|-- README.md
~~~

## 验证

~~~powershell
$env:PYTHONUTF8 = "1"
python "$HOME\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
python -m unittest discover -s scripts/tests -p "test_*.py" -v
ruff check scripts
~~~

验证覆盖 skill 元数据、资源可达性、基准工具行为以及 Python 静态检查。测试输出中的模拟加速比仅用于验证脚本逻辑。性能结论仍需在目标硬件和代表性数据上单独复现；模型效果不能由文档关键词检查或测试数量推断。

## 工程原则

1. 没有测量，不声称加速。
2. 正确性、峰值内存、尾延迟和可移植性可以是硬门槛。
3. 优先减少工作和数据移动，再考虑手写 intrinsics 或自定义 GPU 内核。
4. 每次只验证一个关键候选，未达门槛的候选完整回滚。
5. 区分静态诊断、冒烟测量、受控基准和生产验收，不提升证据等级。

完整工作流见 [SKILL.md](SKILL.md)。
