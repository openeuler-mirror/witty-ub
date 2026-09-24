/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

// B4 C 级浅测：六个模块薄壳的注册/构造/生命周期逻辑
//   - log_local_collector_module / node_local_collector_module / urma_module
//   - lcne_module / database_module / witty_json_module
// 不起网络服务、不监听端口、不连外部 DB：sqlite 一律使用临时目录；
// LcneModule::Start 仅在无 lcne 守护进程（127.0.0.1:34256 无监听）时走确定失败路径。

#include <gtest/gtest.h>

// 标准库与第三方头先于 private→public 宏包含，避免宏污染
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <queue>
#include <sstream>
#include <string>
#include <thread>
#include <tuple>
#include <typeindex>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include <json/json.h>
#include <json/writer.h>
#include <re2/re2.h>
#include <sqlite3.h>

#include "logger.h"

// 打开私有成员用于浅测内部指针状态（本仓库既有测试模式）
#define private public
#include "witty_json_module.h"
#include "database_module.h"
#include "node_local_collector_module.h"
#include "log_local_collector_module.h"
#include "urma_module.h"
#include "lcne_module.h"
#undef private

namespace {

// 打日志的库必须先初始化 log4cplus，否则 SEGFAULT。
struct LoggerInit {
    LoggerInit() { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 每个用例独立的临时目录，析构时清理。
class TempDir {
public:
    TempDir()
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path() /
               ("witty_b4_module_shells_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_);
    }
    ~TempDir()
    {
        std::error_code ec;
        std::filesystem::remove_all(dir_, ec);
    }

    const std::filesystem::path &Path() const { return dir_; }

private:
    std::filesystem::path dir_;
};

// DatabaseModule::Start 打开硬编码路径 /var/witty-ub/euler_copilot_ub：
// 目录存在且可写时才会成功，否则 sqlite 打开失败走 RACK_FAIL。
bool VarWittyDirWritable()
{
    struct stat st = {};
    if (::stat("/var/witty-ub", &st) != 0 || !S_ISDIR(st.st_mode)) {
        return false;
    }
    return ::access("/var/witty-ub", W_OK) == 0;
}

// 构造测试用 Node（单 IP，规避 序列化逗号/反序列化冒号 的已知不一致）
std::shared_ptr<topology::node::Node> MakeNode()
{
    return std::make_shared<topology::node::Node>(1u, 2u, "host-b4", std::vector<std::string>{"10.0.0.1"}, 4u, 8u,
                                                  topology::node::ChipType::CPU);
}

// 构造测试用 UbController（单端口，理由同上）
std::shared_ptr<topology::node::UbController> MakeUbC()
{
    return std::make_shared<topology::node::UbController>("guid-b4", "eid-b4", 10u, 2u, 3u, 4u, "cna-b4",
                                                         std::vector<uint32_t>{100u}, topology::node::DieState::NORMAL,
                                                         topology::node::UbCState::ONLINE);
}

// 构造测试用 Port
std::shared_ptr<topology::node::Port> MakePort()
{
    return std::make_shared<topology::node::Port>(7u, "pcna-b4", "cna-b4", 11u, topology::node::PortState::UP, 8u, 12u,
                                                  13u, 14u, 15u);
}

} // namespace

// ---------------------------------------------------------------------------
// RackModule 框架通用逻辑（CreateModule / GetDependencies / RegArgs）
// ---------------------------------------------------------------------------

// 静态工厂 CreateModule 对六个模块均返回非空实例且类型正确
TEST(RackModuleFactory, CreateModuleReturnsInstanceOfEachShell)
{
    auto log = rack::module::RackModule::CreateModule<failure::log::LogLocalCollectorModule>();
    ASSERT_NE(log, nullptr);
    EXPECT_NE(std::dynamic_pointer_cast<failure::log::LogLocalCollectorModule>(log), nullptr);

    auto node = rack::module::RackModule::CreateModule<topology::node::NodeLocalCollectorModule>();
    ASSERT_NE(node, nullptr);
    EXPECT_NE(std::dynamic_pointer_cast<topology::node::NodeLocalCollectorModule>(node), nullptr);

    auto urma = rack::module::RackModule::CreateModule<urma::module::URMAModule>();
    ASSERT_NE(urma, nullptr);
    EXPECT_NE(std::dynamic_pointer_cast<urma::module::URMAModule>(urma), nullptr);

    auto lcne = rack::module::RackModule::CreateModule<lcne::module::LcneModule>();
    ASSERT_NE(lcne, nullptr);
    EXPECT_NE(std::dynamic_pointer_cast<lcne::module::LcneModule>(lcne), nullptr);

    auto db = rack::module::RackModule::CreateModule<database::DatabaseModule>();
    ASSERT_NE(db, nullptr);
    EXPECT_NE(std::dynamic_pointer_cast<database::DatabaseModule>(db), nullptr);

    auto json = rack::module::RackModule::CreateModule<witty_json::module::JSONModule>();
    ASSERT_NE(json, nullptr);
    EXPECT_NE(std::dynamic_pointer_cast<witty_json::module::JSONModule>(json), nullptr);
}

// 依赖声明：URMA 依赖 JSON 模块；LCNE 依赖 JSON + NodeLocalCollector；其余薄壳无依赖
TEST(ModuleDependencies, AsDeclaredInConstructors)
{
    EXPECT_TRUE(failure::log::LogLocalCollectorModule().GetDependencies().empty());
    EXPECT_TRUE(topology::node::NodeLocalCollectorModule().GetDependencies().empty());
    EXPECT_TRUE(database::DatabaseModule().GetDependencies().empty());
    EXPECT_TRUE(witty_json::module::JSONModule().GetDependencies().empty());

    auto urmaDeps = urma::module::URMAModule().GetDependencies();
    ASSERT_EQ(urmaDeps.size(), 1u);
    EXPECT_EQ(urmaDeps[0], std::type_index(typeid(witty_json::module::JSONModule)));

    auto lcneDeps = lcne::module::LcneModule().GetDependencies();
    ASSERT_EQ(lcneDeps.size(), 2u);
    EXPECT_EQ(lcneDeps[0], std::type_index(typeid(witty_json::module::JSONModule)));
    EXPECT_EQ(lcneDeps[1], std::type_index(typeid(topology::node::NodeLocalCollectorModule)));
}

// 基类 RegArgs 默认空实现：对每个薄壳调用无崩溃
TEST(RackModuleRegArgs, DefaultImplIsNoopForAllShells)
{
    failure::log::LogLocalCollectorModule().RegArgs();
    topology::node::NodeLocalCollectorModule().RegArgs();
    urma::module::URMAModule().RegArgs();
    lcne::module::LcneModule().RegArgs();
    database::DatabaseModule().RegArgs();
    witty_json::module::JSONModule().RegArgs();
    SUCCEED();
}

// ---------------------------------------------------------------------------
// LogLocalCollectorModule
// ---------------------------------------------------------------------------

// 生命周期：未配置命令行参数（UbseContext argMap 为空）时 Initialize 必走失败路径；
// collector 在内部 LogCollector::Initialize 失败前已创建，故 GetCollector 非空
TEST(LogLocalCollectorModule, LifecycleFailsWithoutArgs)
{
    failure::log::LogLocalCollectorModule module;
    // 初始化前 GetCollector 为空
    EXPECT_EQ(module.GetCollector(), nullptr);
    // 缺少 pod-mode 参数（且测试环境无 /var/witty-ub 可写目录）→ RACK_FAIL
    EXPECT_EQ(module.Initialize(), RACK_FAIL);
    // collector_ 已创建
    EXPECT_NE(module.GetCollector(), nullptr);
    // Start/Stop/UnInitialize 成对调用：工具模式下无 reader，Start 恒返回 RACK_OK
    EXPECT_EQ(module.Start(), RACK_OK);
    module.Stop();
    module.UnInitialize();
}

// 重复 Initialize 仍走同一错误路径，不崩溃
TEST(LogLocalCollectorModule, RepeatedInitializeStaysOnErrorPath)
{
    failure::log::LogLocalCollectorModule module;
    EXPECT_EQ(module.Initialize(), RACK_FAIL);
    EXPECT_EQ(module.Initialize(), RACK_FAIL);
    EXPECT_NE(module.GetCollector(), nullptr);
    module.UnInitialize();
}

// ---------------------------------------------------------------------------
// DatabaseModule
// ---------------------------------------------------------------------------

// 未初始化时 GetDatabase 为空；Stop/UnInitialize 对空 db 有保护，可安全调用
TEST(DatabaseModule, AccessorsSafeBeforeInitialize)
{
    database::DatabaseModule module;
    EXPECT_EQ(module.GetDatabase(), nullptr);
    module.Stop();
    module.UnInitialize();
    SUCCEED();
}

// Initialize 创建 Database；Start 使用硬编码路径 /var/witty-ub/euler_copilot_ub，
// 该目录可写时成功、不可写时失败，两者都是无崩溃的确定路径
TEST(DatabaseModule, InitializeCreatesDatabase)
{
    database::DatabaseModule module;
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.GetDatabase(), nullptr);

    const bool writable = VarWittyDirWritable();
    EXPECT_EQ(module.Start(), writable ? RACK_OK : RACK_FAIL);

    // 成对调用 Stop：Close 对未打开/打开失败的句柄均安全
    module.Stop();
    module.UnInitialize();
}

// ---------------------------------------------------------------------------
// NodeLocalCollectorModule
// ---------------------------------------------------------------------------

// 初始化创建 collector；工具模式下 Start/Stop 为空实现且 Start 恒返回 RACK_OK
TEST(NodeLocalCollectorModule, InitializeCreatesCollector)
{
    topology::node::NodeLocalCollectorModule module;
    EXPECT_EQ(module.GetCollector(), nullptr);
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.GetCollector(), nullptr);
    EXPECT_EQ(module.Start(), RACK_OK);
    module.Stop();
    module.UnInitialize();
}

// 带临时 sqlite 库的夹具：Initialize → 注入 DB → 建表
class NodeCollectorModuleWithDb : public ::testing::Test {
protected:
    void SetUp() override
    {
        ASSERT_EQ(module.Initialize(), RACK_OK);
        db = std::make_shared<database::Database>();
        const std::string base = (dir.Path() / "topo_db").string();
        ASSERT_EQ(db->OpenDb(base, true), database::OP_RET::SUCCESS);
        ASSERT_NE(module.GetCollector(), nullptr);
        ASSERT_EQ(module.GetCollector()->InitDb(db), database::OP_RET::SUCCESS);
        ASSERT_EQ(module.GetCollector()->StartDb(), database::OP_RET::SUCCESS);
    }

    TempDir dir;
    topology::node::NodeLocalCollectorModule module;
    std::shared_ptr<database::Database> db;
};

// 空库查询：当前库与历史库查询均返回 RACK_OK 且结果为空
TEST_F(NodeCollectorModuleWithDb, EmptyQueriesSucceed)
{
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(module.QueryCurDeviceData(nodes), RACK_OK);
    EXPECT_EQ(module.QueryCurUbCData(ubcs), RACK_OK);
    EXPECT_EQ(module.QueryCurPortData(ports), RACK_OK);
    EXPECT_EQ(module.QueryHisDeviceData(nodes), RACK_OK);
    EXPECT_EQ(module.QueryHisUbCData(ubcs), RACK_OK);
    EXPECT_EQ(module.QueryHisPortData(ports), RACK_OK);
    EXPECT_TRUE(nodes.empty());
    EXPECT_TRUE(ubcs.empty());
    EXPECT_TRUE(ports.empty());
}

// 设备数据插入 + 当前/历史查询回读
TEST_F(NodeCollectorModuleWithDb, DeviceDataRoundTrip)
{
    std::vector<std::shared_ptr<topology::node::Node>> in{MakeNode()};
    EXPECT_EQ(module.InsertDeviceData(in), RACK_OK);

    std::vector<std::shared_ptr<topology::node::Node>> cur;
    EXPECT_EQ(module.QueryCurDeviceData(cur), RACK_OK);
    ASSERT_EQ(cur.size(), 1u);
    EXPECT_EQ(cur[0]->deviceId, 1u);
    EXPECT_EQ(cur[0]->slotId, 2u);
    EXPECT_EQ(cur[0]->hostname, "host-b4");
    ASSERT_EQ(cur[0]->ipAddrs.size(), 1u);
    EXPECT_EQ(cur[0]->ipAddrs[0], "10.0.0.1");
    EXPECT_EQ(cur[0]->chipNum, 4u);
    EXPECT_EQ(cur[0]->dieNum, 8u);
    EXPECT_EQ(cur[0]->chipType, topology::node::ChipType::CPU);

    std::vector<std::shared_ptr<topology::node::Node>> his;
    EXPECT_EQ(module.QueryHisDeviceData(his), RACK_OK);
    ASSERT_EQ(his.size(), 1u);
    EXPECT_EQ(his[0]->deviceId, 1u);
    EXPECT_EQ(his[0]->hostname, "host-b4");
}

// UbController 数据插入 + 当前/历史查询回读
TEST_F(NodeCollectorModuleWithDb, UbCDataRoundTrip)
{
    std::vector<std::shared_ptr<topology::node::UbController>> in{MakeUbC()};
    EXPECT_EQ(module.InsertUbCData(in), RACK_OK);

    std::vector<std::shared_ptr<topology::node::UbController>> cur;
    EXPECT_EQ(module.QueryCurUbCData(cur), RACK_OK);
    ASSERT_EQ(cur.size(), 1u);
    EXPECT_EQ(cur[0]->dieGuid, "guid-b4");
    EXPECT_EQ(cur[0]->ubcEid, "eid-b4");
    EXPECT_EQ(cur[0]->deviceId, 10u);
    EXPECT_EQ(cur[0]->slotId, 2u);
    EXPECT_EQ(cur[0]->chipId, 3u);
    EXPECT_EQ(cur[0]->dieId, 4u);
    EXPECT_EQ(cur[0]->primaryCna, "cna-b4");
    ASSERT_EQ(cur[0]->portIds.size(), 1u);
    EXPECT_EQ(cur[0]->portIds[0], 100u);
    EXPECT_EQ(cur[0]->dieState, topology::node::DieState::NORMAL);
    EXPECT_EQ(cur[0]->ubcState, topology::node::UbCState::ONLINE);

    std::vector<std::shared_ptr<topology::node::UbController>> his;
    EXPECT_EQ(module.QueryHisUbCData(his), RACK_OK);
    ASSERT_EQ(his.size(), 1u);
    EXPECT_EQ(his[0]->primaryCna, "cna-b4");
}

// 端口数据插入：Port::ObjToDataMap 把 remoteIouId 误写为 "remoteIiId"（不存在的列），
// 导致插入必然失败——此处断言当前行为（生产 bug 仅报告，勿修）
TEST_F(NodeCollectorModuleWithDb, PortDataInsertFailsDueToKeyTypo)
{
    std::vector<std::shared_ptr<topology::node::Port>> in{MakePort()};
    EXPECT_EQ(module.InsertPortData(in), RACK_FAIL);

    // 插入失败后查询不产生数据，但查询本身成功
    std::vector<std::shared_ptr<topology::node::Port>> cur;
    EXPECT_EQ(module.QueryCurPortData(cur), RACK_OK);
    EXPECT_TRUE(cur.empty());
}

// ---------------------------------------------------------------------------
// URMAModule
// ---------------------------------------------------------------------------

// Initialize 创建 URMATopology；Start 在 UbseContext 未解析参数（podMode 为空）时
// 走 CreateTopology 的"Unknown pod mode"错误分支，纯内存判断、无任何 IO
TEST(URMAModule, InitializeCreatesTopologyAndStartFailsWithoutPodMode)
{
    urma::module::URMAModule module;
    EXPECT_EQ(module.urmaTopology, nullptr);
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.urmaTopology, nullptr);

    EXPECT_EQ(module.Start(), RACK_FAIL);
    module.Stop();
    module.UnInitialize();
}

// ---------------------------------------------------------------------------
// LcneModule
// ---------------------------------------------------------------------------

// Initialize 创建 LcneTopology；Stop/UnInitialize 为空实现
TEST(LcneModule, InitializeCreatesTopology)
{
    lcne::module::LcneModule module;
    EXPECT_EQ(module.lcneTopology, nullptr);
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.lcneTopology, nullptr);
    module.Stop();
    module.UnInitialize();
}

// Start：测试机上无 lcne 守护进程监听 127.0.0.1:34256，采集必然失败 → RACK_FAIL
// （连接回环端口立即被拒绝，既不起服务也不监听端口）
TEST(LcneModule, StartFailsWithoutLcneDaemon)
{
    lcne::module::LcneModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    EXPECT_EQ(module.Start(), RACK_FAIL);
    module.Stop();
    module.UnInitialize();
}

// ---------------------------------------------------------------------------
// JSONModule
// ---------------------------------------------------------------------------

// Initialize 创建 WittyJson；Start/Stop/UnInitialize 成对调用
TEST(JSONModule, InitializeCreatesJsonIo)
{
    witty_json::module::JSONModule module;
    EXPECT_EQ(module.json_io, nullptr);
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.json_io, nullptr);
    EXPECT_EQ(module.Start(), RACK_OK);
    module.Stop();
    module.UnInitialize();
}

// GetJsonPair 返回键名与原 vector 的引用（不拷贝数据）
TEST(JSONModule, GetJsonPairHoldsKeyAndReference)
{
    witty_json::module::JSONModule module;
    std::vector<topology::node::UbController> ubcs;
    auto ubcPair = module.GetJsonPair("iodie", ubcs);
    EXPECT_STREQ(ubcPair.first, "iodie");
    // second 即原 vector 的引用（make_pair 对 std::ref 剥离 reference_wrapper）
    EXPECT_EQ(&ubcPair.second, &ubcs);

    std::vector<topology::node::Port> ports;
    auto portPair = module.GetJsonPair("port", ports);
    EXPECT_STREQ(portPair.first, "port");
    EXPECT_EQ(&portPair.second, &ports);
}

// WriteVectorsToFile 成功路径：写临时目录并原子改名，锁文件被清理，内容可回读
TEST(JSONModule, WriteVectorsToFileWritesValidJson)
{
    witty_json::module::JSONModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);

    TempDir dir;
    const std::string file = (dir.Path() / "topology.json").string();
    std::vector<topology::node::UbController> ubcs;
    ubcs.push_back(*MakeUbC());
    std::vector<topology::node::Port> ports;
    ports.push_back(*MakePort());
    auto ubcPair = module.GetJsonPair("iodie", ubcs);
    auto portPair = module.GetJsonPair("port", ports);

    EXPECT_EQ(module.WriteVectorsToFile(file, ubcPair, portPair), RACK_OK);
    // 目标文件存在，锁文件已清理
    EXPECT_TRUE(std::filesystem::exists(file));
    EXPECT_FALSE(std::filesystem::exists(file + ".lock"));

    // 回读并校验 JSON 内容
    std::ifstream in(file);
    ASSERT_TRUE(in.is_open());
    Json::CharReaderBuilder builder;
    std::string errs;
    Json::Value root;
    ASSERT_TRUE(Json::parseFromStream(builder, in, &root, &errs)) << errs;
    ASSERT_TRUE(root["iodie"].isArray());
    ASSERT_EQ(root["iodie"].size(), 1u);
    EXPECT_EQ(root["iodie"][0]["slot_id"].asUInt(), 2u);
    EXPECT_EQ(root["iodie"][0]["ubpu_id"].asUInt(), 3u);
    EXPECT_EQ(root["iodie"][0]["iou_id"].asUInt(), 4u);
    EXPECT_EQ(root["iodie"][0]["primary_cna"].asString(), "cna-b4");
    ASSERT_TRUE(root["port"].isArray());
    ASSERT_EQ(root["port"].size(), 1u);
    EXPECT_EQ(root["port"][0]["port_id"].asUInt(), 7u);
    EXPECT_EQ(root["port"][0]["primary_cna"].asString(), "cna-b4");
    EXPECT_EQ(root["port"][0]["remote_port_id"].asUInt(), 8u);
}

// WriteVectorsToFile 失败路径：把已存在的普通文件当目录用 → 打不开锁文件 → RACK_FAIL
TEST(JSONModule, WriteVectorsToFileFailsOnInvalidDirectory)
{
    witty_json::module::JSONModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);

    // /tmp 下先放一个普通文件，再以 “文件/xxx” 为目标路径 → open(ENOTDIR) 失败
    TempDir dir;
    const std::filesystem::path blocker = dir.Path() / "blocker";
    {
        std::ofstream out(blocker);
        ASSERT_TRUE(out.is_open());
    }
    std::vector<topology::node::UbController> ubcs;
    ubcs.push_back(*MakeUbC());
    auto ubcPair = module.GetJsonPair("iodie", ubcs);
    EXPECT_EQ(module.WriteVectorsToFile((blocker / "topology.json").string(), ubcPair), RACK_FAIL);
}
