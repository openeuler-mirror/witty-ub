/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2/
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

// B3 B 级：witty_json 库——WittyJson 模板写文件与 JSONModule 增量路径。
// 与 test_module_shells.cpp 的 JSONModule 部分互补：那边覆盖模块生命周期与基础成败路径，
// 这里聚焦可变参数模板 add_vector_to_json 的展开、临时文件/锁文件的命名与清理、
// rename 原子替换的各失败分支（临时文件被目录占用 / 目标为目录 / 父目录缺失）。

#include <gtest/gtest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

#include <json/json.h>
#include <json/writer.h>

#include "urma_data_def.h"
#include "witty_json.h"
#include "witty_json_module.h"

// ---------------------------------------------------------------------------
// log4cplus 链接桩：本目标仅链接 witty_json（jsoncpp 为 PRIVATE，未传递 log4cplus），
// 而 rack logger.h 的 LogStream 析构运行期会引用 log4cplus 符号。
// 此处不调用 rack::logger::init（会引入 ConsoleAppender/PatternLayout 等更多依赖），
// g_logger 保持默认构造、isEnabledFor 恒 false，所有日志被安全丢弃。
// ---------------------------------------------------------------------------
namespace log4cplus {
namespace helpers {
// SharedObjectPtr<Appender> 模板实例化时引用（构造/析构路径）
void SharedObject::addReference() const LOG4CPLUS_NOEXCEPT {}
void SharedObject::removeReference() const {}
} // namespace helpers
namespace spi {
// 纯虚析构仍需定义（Logger 虚基类析构路径引用）
AppenderAttachable::~AppenderAttachable() {}
} // namespace spi
Logger::Logger() LOG4CPLUS_NOEXCEPT {}
Logger::~Logger() {}
bool Logger::isEnabledFor(LogLevel) const
{
    return false;
}
// 以下 override 定义使 vtable 在本 TU 生成（key function 为 addAppender）
void Logger::addAppender(SharedAppenderPtr) {}
SharedAppenderPtrList Logger::getAllAppenders()
{
    return SharedAppenderPtrList();
}
SharedAppenderPtr Logger::getAppender(const log4cplus::tstring &)
{
    return SharedAppenderPtr();
}
void Logger::removeAllAppenders() {}
void Logger::removeAppender(SharedAppenderPtr) {}
void Logger::removeAppender(const log4cplus::tstring &) {}
namespace detail {
tostringstream &get_macro_body_oss()
{
    static tostringstream oss;
    return oss;
}
void macro_forced_log(Logger const &, LogLevel, tstring const &, char const *, int, char const *) {}
} // namespace detail
} // namespace log4cplus

namespace {
// 每个用例独立的临时目录，析构时清理
class TempDir {
public:
    TempDir()
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path() /
               ("witty_b3_json_test_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_);
    }
    ~TempDir() { std::filesystem::remove_all(dir_); }
    const std::filesystem::path &Path() const { return dir_; }

private:
    std::filesystem::path dir_;
};

// 回读 JSON 文件并解析为 Json::Value；失败则终止用例
Json::Value ReadJsonFile(const std::string &file)
{
    std::ifstream in(file);
    EXPECT_TRUE(in.is_open()) << "cannot open " << file;
    Json::CharReaderBuilder builder;
    std::string errs;
    Json::Value root;
    EXPECT_TRUE(Json::parseFromStream(builder, in, &root, &errs)) << errs;
    return root;
}
} // namespace

class WittyJsonTest : public ::testing::Test {
protected:
    witty_json::io::WittyJson json;
    TempDir dir;
};

// 零个 pair：写出空 JSON 对象
TEST_F(WittyJsonTest, NoPairWritesEmptyObject)
{
    const std::string file = (dir.Path() / "empty.json").string();
    EXPECT_EQ(json.WriteVectorsToFile(file), RACK_OK);
    Json::Value root = ReadJsonFile(file);
    EXPECT_TRUE(root.isObject());
    EXPECT_EQ(root.size(), 0u);
}

// 空 vector：写出空数组；多个不同业务类型的 vector 一次写出
TEST_F(WittyJsonTest, EmptyVectorsProduceEmptyArrays)
{
    const std::string file = (dir.Path() / "empty_vec.json").string();
    std::vector<topology::urma::Pod> pods;
    std::vector<topology::urma::URMADevice> devices;
    std::pair<const char *, const std::vector<topology::urma::Pod> &> podPair("pod", pods);
    std::pair<const char *, const std::vector<topology::urma::URMADevice> &> devPair("device", devices);
    EXPECT_EQ(json.WriteVectorsToFile(file, podPair, devPair), RACK_OK);

    Json::Value root = ReadJsonFile(file);
    ASSERT_TRUE(root["pod"].isArray());
    EXPECT_EQ(root["pod"].size(), 0u);
    ASSERT_TRUE(root["device"].isArray());
    EXPECT_EQ(root["device"].size(), 0u);
}

// 三种类型混合（Pod/Jetty/URMADevice），校验 to_json 序列化内容与 optional 字段行为
TEST_F(WittyJsonTest, MultiplePairsOfDifferentTypes)
{
    const std::string file = (dir.Path() / "mixed.json").string();
    std::vector<topology::urma::Pod> pods{topology::urma::Pod("pod-1"), topology::urma::Pod("pod-2")};
    std::vector<topology::urma::Jetty> jetties{
        // 无 podId：to_json 不写 pod_id 键
        topology::urma::Jetty("j-local-1", "eid-local-1", "j-remote-1", "eid-remote-1"),
        // 有 podId：写出 pod_id
        topology::urma::Jetty("j-local-2", "eid-local-2", "j-remote-2", "eid-remote-2", "pod-1")};
    std::vector<topology::urma::URMADevice> devices{topology::urma::URMADevice("eid-dev-1")};
    std::pair<const char *, const std::vector<topology::urma::Pod> &> podPair("pod", pods);
    std::pair<const char *, const std::vector<topology::urma::Jetty> &> jettyPair("jetty", jetties);
    std::pair<const char *, const std::vector<topology::urma::URMADevice> &> devPair("urma_device", devices);
    EXPECT_EQ(json.WriteVectorsToFile(file, podPair, jettyPair, devPair), RACK_OK);

    Json::Value root = ReadJsonFile(file);
    ASSERT_EQ(root.size(), 3u);
    // pod 数组
    ASSERT_EQ(root["pod"].size(), 2u);
    EXPECT_EQ(root["pod"][0]["pod_id"].asString(), "pod-1");
    EXPECT_EQ(root["pod"][1]["pod_id"].asString(), "pod-2");
    // jetty 数组：可选字段有无的两种分支
    ASSERT_EQ(root["jetty"].size(), 2u);
    EXPECT_EQ(root["jetty"][0]["local_jetty_id"].asString(), "j-local-1");
    EXPECT_EQ(root["jetty"][0]["local_eid"].asString(), "eid-local-1");
    EXPECT_EQ(root["jetty"][0]["remote_jetty_id"].asString(), "j-remote-1");
    EXPECT_EQ(root["jetty"][0]["remote_eid"].asString(), "eid-remote-1");
    EXPECT_FALSE(root["jetty"][0].isMember("pod_id"));
    EXPECT_EQ(root["jetty"][1]["pod_id"].asString(), "pod-1");
    // urma_device 数组
    ASSERT_EQ(root["urma_device"].size(), 1u);
    EXPECT_EQ(root["urma_device"][0]["device_id"].asString(), "eid-dev-1");
}

// 临时文件命名规则：a.b.json -> a.b.tmp.json；成功后临时文件与锁文件均被清理
TEST_F(WittyJsonTest, TempAndLockFilesCleanedUpAfterSuccess)
{
    const std::string file = (dir.Path() / "a.b.json").string();
    const std::string tempFile = (dir.Path() / "a.b.tmp.json").string();
    const std::string lockFile = file + ".lock";
    std::vector<topology::urma::Pod> pods{topology::urma::Pod("pod-x")};
    std::pair<const char *, const std::vector<topology::urma::Pod> &> podPair("pod", pods);
    EXPECT_EQ(json.WriteVectorsToFile(file, podPair), RACK_OK);

    EXPECT_TRUE(std::filesystem::exists(file));
    EXPECT_FALSE(std::filesystem::exists(tempFile));
    EXPECT_FALSE(std::filesystem::exists(lockFile));
    // 目录中除目标文件外无其他残留（lock 已删除）
    size_t fileCnt = 0;
    for (const auto &entry : std::filesystem::directory_iterator(dir.Path())) {
        (void)entry;
        ++fileCnt;
    }
    EXPECT_EQ(fileCnt, 1u);
}

// 已有旧内容的文件被原子替换：旧键消失，仅保留本次写入的内容
TEST_F(WittyJsonTest, OverwritesExistingFileContent)
{
    const std::string file = (dir.Path() / "reuse.json").string();
    {
        std::ofstream out(file);
        out << "{\"stale_key\": [1, 2, 3]}";
    }
    std::vector<topology::urma::URMADevice> devices{topology::urma::URMADevice("eid-new")};
    std::pair<const char *, const std::vector<topology::urma::URMADevice> &> devPair("device", devices);
    EXPECT_EQ(json.WriteVectorsToFile(file, devPair), RACK_OK);

    Json::Value root = ReadJsonFile(file);
    EXPECT_FALSE(root.isMember("stale_key"));
    ASSERT_TRUE(root["device"].isArray());
    EXPECT_EQ(root["device"].size(), 1u);
    EXPECT_EQ(root["device"][0]["device_id"].asString(), "eid-new");
}

// 父目录不存在：lock 文件打开失败（ENOENT）-> RACK_FAIL
TEST_F(WittyJsonTest, FailsWhenParentDirectoryMissing)
{
    const std::string file = (dir.Path() / "no_such_dir" / "out.json").string();
    std::vector<topology::urma::Pod> pods;
    std::pair<const char *, const std::vector<topology::urma::Pod> &> podPair("pod", pods);
    EXPECT_EQ(json.WriteVectorsToFile(file, podPair), RACK_FAIL);
    EXPECT_FALSE(std::filesystem::exists(file));
}

// 临时文件路径被同名目录占用：ofstream 打开失败 -> RACK_FAIL；
// 失败路径只解锁不删除锁文件（当前行为），目标文件不生成
TEST_F(WittyJsonTest, FailsWhenTempPathOccupiedByDirectory)
{
    const std::string file = (dir.Path() / "topology.json").string();
    const std::string tempFile = (dir.Path() / "topology.tmp.json").string();
    const std::string lockFile = file + ".lock";
    ASSERT_TRUE(std::filesystem::create_directories(tempFile));

    std::vector<topology::urma::Pod> pods{topology::urma::Pod("pod-1")};
    std::pair<const char *, const std::vector<topology::urma::Pod> &> podPair("pod", pods);
    EXPECT_EQ(json.WriteVectorsToFile(file, podPair), RACK_FAIL);
    // 目标文件未生成，锁文件残留（失败分支不清理）
    EXPECT_FALSE(std::filesystem::exists(file));
    EXPECT_TRUE(std::filesystem::exists(lockFile));
}

// 目标路径是已存在目录：rename 抛 filesystem_error -> RACK_FAIL；
// 临时文件在失败分支被显式清理，锁文件残留
TEST_F(WittyJsonTest, FailsWhenTargetIsExistingDirectory)
{
    const std::string file = (dir.Path() / "as_dir").string();
    const std::string tempFile = (dir.Path() / "as_dir.tmp").string();
    const std::string lockFile = file + ".lock";
    ASSERT_TRUE(std::filesystem::create_directories(file));

    std::vector<topology::urma::URMADevice> devices{topology::urma::URMADevice("eid-1")};
    std::pair<const char *, const std::vector<topology::urma::URMADevice> &> devPair("device", devices);
    EXPECT_EQ(json.WriteVectorsToFile(file, devPair), RACK_FAIL);
    // 临时文件被失败分支删除；目标目录原样保留；锁文件残留
    EXPECT_FALSE(std::filesystem::exists(tempFile));
    EXPECT_TRUE(std::filesystem::is_directory(file));
    EXPECT_TRUE(std::filesystem::exists(lockFile));
}

// ---------------------------------------------------------------------------
// JSONModule 增量路径（生命周期与基础成败已在 test_module_shells 覆盖）
// ---------------------------------------------------------------------------

// WriteVectorsToFile 转发失败路径（模块层捕获 RACK_FAIL 原样返回）
TEST(JSONModuleIncrement, WriteForwardsFailure)
{
    witty_json::module::JSONModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);

    TempDir dir;
    const std::string file = (dir.Path() / "missing_parent" / "out.json").string();
    std::vector<topology::urma::Pod> pods{topology::urma::Pod("pod-1")};
    auto podPair = module.GetJsonPair("pod", pods);
    EXPECT_EQ(module.WriteVectorsToFile(file, podPair), RACK_FAIL);
    EXPECT_FALSE(std::filesystem::exists(file));
}

// GetJsonPair 对 urma 类型的行为：键名一致且 second 引用原 vector（不拷贝）
TEST(JSONModuleIncrement, GetJsonPairHoldsKeyAndReferenceForUrmaTypes)
{
    witty_json::module::JSONModule module;
    std::vector<topology::urma::Pod> pods{topology::urma::Pod("pod-r")};
    auto podPair = module.GetJsonPair("pod", pods);
    EXPECT_STREQ(podPair.first, "pod");
    EXPECT_EQ(&podPair.second, &pods);

    std::vector<topology::urma::Jetty> jetties{
        topology::urma::Jetty("j", "e", "rj", "re", "pod-r")};
    auto jettyPair = module.GetJsonPair("jetty", jetties);
    EXPECT_STREQ(jettyPair.first, "jetty");
    EXPECT_EQ(&jettyPair.second, &jetties);
}
