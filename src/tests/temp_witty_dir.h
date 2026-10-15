/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
 */
#pragma once

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

// 测试公共 RAII 临时 WITTY_DIR：构造时预建 data/ 下的业务子目录，析构整树清理。
class TempWittyDir {
public:
    explicit TempWittyDir(const std::string &prefix = "witty_diag_test",
                          const std::vector<std::string> &dataSubdirs = {})
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path()
                   .append(prefix + "_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                           "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_);
        for (const auto &sub : dataSubdirs) {
            std::filesystem::path dataDir = dir_;
            dataDir.append("data").append(sub);
            std::filesystem::create_directories(dataDir);
        }
    }

    ~TempWittyDir() { std::filesystem::remove_all(dir_); }

    const std::filesystem::path &Path() const { return dir_; }

    // 写文件（自动创建父目录）。
    void Write(const std::string &relPath, const std::string &content)
    {
        std::filesystem::path file = dir_;
        file.append(relPath);
        std::filesystem::create_directories(file.parent_path());
        std::ofstream out(file, std::ios::binary);
        out << content;
    }

private:
    std::filesystem::path dir_;
};
