/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
 */
#pragma once

#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

// 测试公共 RAII 临时目录：构造创建、析构整树清理。
class TempDir {
public:
    explicit TempDir(const std::string &prefix = "witty_test")
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path()
                   .append(prefix + "_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                           "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_);
    }

    ~TempDir() { std::filesystem::remove_all(dir_); }

    const std::filesystem::path &Path() const { return dir_; }

    // 写文件（自动创建父目录），返回文件完整路径。
    std::string Write(const std::string &relPath, const std::string &content)
    {
        std::filesystem::path file = dir_;
        file.append(relPath);
        std::filesystem::create_directories(file.parent_path());
        std::ofstream out(file, std::ios::binary);
        out << content;
        return file.string();
    }

    // 读整个文件。
    std::string Read(const std::string &relPath) const
    {
        std::filesystem::path file = dir_;
        file.append(relPath);
        std::ifstream in(file);
        std::stringstream buffer;
        buffer << in.rdbuf();
        return buffer.str();
    }

private:
    std::filesystem::path dir_;
};
