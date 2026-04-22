# CMake + GCC 13 toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++-13 gcc-13 cmake make \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 100 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-13
