/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A
 * PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#include <gtest/gtest.h>

#include <chrono>
#include <filesystem>
#include <limits>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "logger.h"
#include "node_collector.h"

namespace {
// 打日志的库必须先初始化 log4cplus，否则 SEGFAULT
struct LoggerInit {
    LoggerInit() { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 每个用例独立的临时目录（sqlite 库文件也落在这里），析构时清理
class TempDir {
public:
    TempDir()
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path() /
               ("witty_node_collector_test_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_);
    }
    ~TempDir() { std::filesystem::remove_all(dir_); }
    const std::filesystem::path &Path() const { return dir_; }

private:
    std::filesystem::path dir_;
};
} // namespace

// 每个用例使用独立的临时 sqlite 库（含 _history 历史库）
class NodeCollectorTest : public ::testing::Test {
protected:
    void SetUp() override
    {
        db = std::make_shared<database::Database>();
        ASSERT_EQ(db->OpenDb((dir.Path() / "nodes.db").string(), true), database::OP_RET::SUCCESS);
        ASSERT_EQ(collector.InitDb(db), database::OP_RET::SUCCESS);
        ASSERT_EQ(collector.StartDb(), database::OP_RET::SUCCESS);
    }
    void TearDown() override { db->Close(); }

    TempDir dir;
    std::shared_ptr<database::Database> db;
    topology::node::NodeCollector collector;
};

TEST(NodeCollectorStandalone, GetDbWithoutInitReturnsNull)
{
    topology::node::NodeCollector collector;
    EXPECT_EQ(collector.GetDb(), nullptr);
}

TEST_F(NodeCollectorTest, InitAndStartDb)
{
    // InitDb 持有库句柄
    EXPECT_EQ(collector.GetDb(), db);
    // StartDb 已注册 Device/UbController/Port 表：合法表可查询，未注册表失败
    database::QueryResult res;
    EXPECT_EQ(db->QueryCurrData("Device", {}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(db->QueryCurrData("UbController", {}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(db->QueryCurrData("Port", {}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(db->QueryCurrData("NoSuchTable", {}, &res), database::OP_RET::FAIL);
    // 建表语句幂等（CREATE TABLE IF NOT EXISTS）
    EXPECT_EQ(collector.StartDb(), database::OP_RET::SUCCESS);
}

TEST_F(NodeCollectorTest, InsertAndQueryDeviceRoundTrip)
{
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    nodes.push_back(std::make_shared<topology::node::Node>(1, 2, "host-a", std::vector<std::string>{"10.0.0.1"}, 4, 8,
                                                            topology::node::ChipType::CPU));
    nodes.push_back(std::make_shared<topology::node::Node>(2, 3, "host-b", std::vector<std::string>{"10.0.0.2"}, 8, 16,
                                                            topology::node::ChipType::NPU));
    EXPECT_EQ(collector.InsertDeviceData(nodes), database::OP_RET::SUCCESS);

    // 当前库查询
    std::vector<std::shared_ptr<topology::node::Node>> curr;
    EXPECT_EQ(collector.QueryCurDeviceData(curr), database::OP_RET::SUCCESS);
    ASSERT_EQ(curr.size(), 2u);
    // SELECT 无 ORDER BY，按 deviceId 建索引再断言
    std::unordered_map<uint32_t, topology::node::Node> byId;
    for (const auto &n : curr) {
        byId[n->deviceId] = *n;
    }
    ASSERT_EQ(byId.size(), 2u);
    EXPECT_EQ(byId[1].slotId, 2u);
    EXPECT_EQ(byId[1].hostname, "host-a");
    EXPECT_EQ(byId[1].ipAddrs, std::vector<std::string>({"10.0.0.1"}));
    EXPECT_EQ(byId[1].chipNum, 4u);
    EXPECT_EQ(byId[1].dieNum, 8u);
    EXPECT_EQ(byId[1].chipType, topology::node::ChipType::CPU);
    EXPECT_EQ(byId[2].chipType, topology::node::ChipType::NPU);

    // 历史库查询（enableHis 时插入双写）
    std::vector<std::shared_ptr<topology::node::Node>> his;
    EXPECT_EQ(collector.QueryHisNodeData(his), database::OP_RET::SUCCESS);
    EXPECT_EQ(his.size(), 2u);
}

TEST_F(NodeCollectorTest, DeviceSamePrimaryKeyTriggersUpdate)
{
    std::vector<std::shared_ptr<topology::node::Node>> first;
    first.push_back(std::make_shared<topology::node::Node>(1, 2, "host-a", std::vector<std::string>{"10.0.0.1"}, 4, 8,
                                                           topology::node::ChipType::CPU));
    EXPECT_EQ(collector.InsertDeviceData(first), database::OP_RET::SUCCESS);
    // 保证两次插入的毫秒时间戳不同：同毫秒时历史库主键 (deviceId, update_timestamp) 会 UNIQUE 冲突
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    // 同主键 deviceId 再插入 -> 走更新分支
    std::vector<std::shared_ptr<topology::node::Node>> second;
    second.push_back(std::make_shared<topology::node::Node>(1, 9, "host-b", std::vector<std::string>{"10.0.0.9"}, 1, 2,
                                                           topology::node::ChipType::CPULINK));
    EXPECT_EQ(collector.InsertDeviceData(second), database::OP_RET::SUCCESS);

    std::vector<std::shared_ptr<topology::node::Node>> curr;
    EXPECT_EQ(collector.QueryCurDeviceData(curr), database::OP_RET::SUCCESS);
    // 当前库仅一行且内容为最新
    ASSERT_EQ(curr.size(), 1u);
    EXPECT_EQ(curr[0]->hostname, "host-b");
    EXPECT_EQ(curr[0]->slotId, 9u);

    // 历史库保留两代记录（旧记录被置 expire，新记录新增）。
    // 注：QueryHisNodeData 封装默认 start=0，而 GetNowTimestamp() 将毫秒时间戳截断为 int
    // 当前为负值，导致已置 expire 的旧行 (expire < 0) 全部被过滤，故直连宽窗口验证双代记录
    database::QueryResult hisRes;
    EXPECT_EQ(db->QueryHisData("Device", {}, &hisRes, std::numeric_limits<int>::min(),
                               std::numeric_limits<int>::max()),
              database::OP_RET::SUCCESS);
    ASSERT_EQ(hisRes.size(), 2u);
    // 两代记录：旧记录 expire 为时间戳，新记录 expire 为 SQL NULL
    // （QueryPrepared 将 SQL NULL 序列化为字面量 "NULL" 字符串）
    int expiredCnt = 0;
    int activeCnt = 0;
    for (const auto &row : hisRes) {
        const std::string &expire = row.at("expire_timestamp");
        expire == "NULL" || expire.empty() ? ++activeCnt : ++expiredCnt;
    }
    EXPECT_EQ(expiredCnt, 1);
    EXPECT_EQ(activeCnt, 1);
}

TEST_F(NodeCollectorTest, InsertAndQueryUbCRoundTrip)
{
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    ubcs.push_back(std::make_shared<topology::node::UbController>("guid-1", "eid-1", 1, 2, 3, 4, "cna-1", std::vector<uint32_t>{5},
                                                                 topology::node::DieState::NORMAL,
                                                                 topology::node::UbCState::ONLINE));
    EXPECT_EQ(collector.InsertUbCData(ubcs), database::OP_RET::SUCCESS);

    std::vector<std::shared_ptr<topology::node::UbController>> curr;
    EXPECT_EQ(collector.QueryCurUbCData(curr), database::OP_RET::SUCCESS);
    ASSERT_EQ(curr.size(), 1u);
    EXPECT_EQ(curr[0]->dieGuid, "guid-1");
    EXPECT_EQ(curr[0]->ubcEid, "eid-1");
    EXPECT_EQ(curr[0]->deviceId, 1u);
    EXPECT_EQ(curr[0]->slotId, 2u);
    EXPECT_EQ(curr[0]->chipId, 3u);
    EXPECT_EQ(curr[0]->dieId, 4u);
    EXPECT_EQ(curr[0]->primaryCna, "cna-1");
    EXPECT_EQ(curr[0]->portIds, std::vector<uint32_t>({5}));
    EXPECT_EQ(curr[0]->dieState, topology::node::DieState::NORMAL);
    EXPECT_EQ(curr[0]->ubcState, topology::node::UbCState::ONLINE);

    std::vector<std::shared_ptr<topology::node::UbController>> his;
    EXPECT_EQ(collector.QueryHisUbCData(his), database::OP_RET::SUCCESS);
    EXPECT_EQ(his.size(), 1u);
}

TEST_F(NodeCollectorTest, UbCSamePrimaryKeyTriggersUpdate)
{
    std::vector<std::shared_ptr<topology::node::UbController>> first;
    first.push_back(std::make_shared<topology::node::UbController>("guid-1", "eid-1", 1, 2, 3, 4, "cna-1", std::vector<uint32_t>{5},
                                                                   topology::node::DieState::NORMAL,
                                                                   topology::node::UbCState::ONLINE));
    EXPECT_EQ(collector.InsertUbCData(first), database::OP_RET::SUCCESS);
    // 保证两次插入的毫秒时间戳不同：同毫秒时历史库主键 (primaryCna, update_timestamp) 会 UNIQUE 冲突，
    // 触发 InsertData 内 UpdateData 分支插入历史库失败，整体返回 FAIL
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    // UbController 主键为 primaryCna：同 primaryCna 再插入走更新
    std::vector<std::shared_ptr<topology::node::UbController>> second;
    second.push_back(std::make_shared<topology::node::UbController>("guid-2", "eid-2", 9, 8, 7, 6, "cna-1", std::vector<uint32_t>{6},
                                                                     topology::node::DieState::ABNORMAL,
                                                                     topology::node::UbCState::OFFLINE));
    EXPECT_EQ(collector.InsertUbCData(second), database::OP_RET::SUCCESS);

    std::vector<std::shared_ptr<topology::node::UbController>> curr;
    EXPECT_EQ(collector.QueryCurUbCData(curr), database::OP_RET::SUCCESS);
    ASSERT_EQ(curr.size(), 1u);
    EXPECT_EQ(curr[0]->dieGuid, "guid-2");
    EXPECT_EQ(curr[0]->ubcState, topology::node::UbCState::OFFLINE);

    // 历史库保留两代记录（同上：绕开默认窗口，直连宽窗口验证）
    database::QueryResult hisRes;
    EXPECT_EQ(db->QueryHisData("UbController", {}, &hisRes, std::numeric_limits<int>::min(),
                               std::numeric_limits<int>::max()),
              database::OP_RET::SUCCESS);
    ASSERT_EQ(hisRes.size(), 2u);
    // 旧代 dieGuid=guid-1，新代 dieGuid=guid-2
    int oldCnt = 0;
    int newCnt = 0;
    for (const auto &row : hisRes) {
        if (row.at("dieGuid") == "guid-1") {
            ++oldCnt;
        } else if (row.at("dieGuid") == "guid-2") {
            ++newCnt;
        }
    }
    EXPECT_EQ(oldCnt, 1);
    EXPECT_EQ(newCnt, 1);
}

// 生产 bug（只记录不修改）：Port::ObjToDataMap 写出键 "remoteIiId"，
// 而表列名为 remoteIouId，导致 InsertPortData 必然失败
TEST_F(NodeCollectorTest, InsertPortDataFailsOnRemoteIiIdKey)
{
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    ports.push_back(std::make_shared<topology::node::Port>(101, "cna-1", "primary-cna", 1,
                                                           topology::node::PortState::UP, 201, 202, 203, 204, 205));
    EXPECT_EQ(collector.InsertPortData(ports), database::OP_RET::FAIL);
    // 无任何数据写入
    database::QueryResult res;
    EXPECT_EQ(db->QueryCurrData("Port", {}, &res), database::OP_RET::SUCCESS);
    EXPECT_TRUE(res.empty());
}

// 生产 bug（只记录不修改）：DataMapToObj(Port) 读键 "remotePortIds"/"remoteIouId"，
// 与表列名 remotePortId 不符，命中行时 stoi 解析空串抛异常
TEST_F(NodeCollectorTest, QueryPortDataThrowsOnExistingRows)
{
    // 绕过有 bug 的 ObjToDataMap，按表结构直接插入一行
    database::DataMap row = {{"portId", "101"},
                             {"portCna", "cna-1"},
                             {"primaryCna", "primary-cna"},
                             {"deviceId", "1"},
                             {"portState", "UP"},
                             {"remotePortId", "201"},
                             {"remoteDeviceId", "202"},
                             {"remoteSlotId", "203"},
                             {"remoteUbpuId", "204"},
                             {"remoteIouId", "205"}};
    EXPECT_EQ(db->InsertData("Port", row), database::OP_RET::SUCCESS);

    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_ANY_THROW(collector.QueryCurPortData(ports));
    std::vector<std::shared_ptr<topology::node::Port>> hisPorts;
    EXPECT_ANY_THROW(collector.QueryHisPortData(hisPorts));
}

TEST_F(NodeCollectorTest, EmptyInsertAndQuery)
{
    // 空列表插入：直接成功
    std::vector<std::shared_ptr<topology::node::Node>> nodes;
    EXPECT_EQ(collector.InsertDeviceData(nodes), database::OP_RET::SUCCESS);
    std::vector<std::shared_ptr<topology::node::UbController>> ubcs;
    EXPECT_EQ(collector.InsertUbCData(ubcs), database::OP_RET::SUCCESS);
    std::vector<std::shared_ptr<topology::node::Port>> ports;
    EXPECT_EQ(collector.InsertPortData(ports), database::OP_RET::SUCCESS);

    // 空表查询：六个查询接口均成功且为空
    EXPECT_EQ(collector.QueryHisNodeData(nodes), database::OP_RET::SUCCESS);
    EXPECT_TRUE(nodes.empty());
    EXPECT_EQ(collector.QueryHisUbCData(ubcs), database::OP_RET::SUCCESS);
    EXPECT_TRUE(ubcs.empty());
    EXPECT_EQ(collector.QueryHisPortData(ports), database::OP_RET::SUCCESS);
    EXPECT_TRUE(ports.empty());
    EXPECT_EQ(collector.QueryCurDeviceData(nodes), database::OP_RET::SUCCESS);
    EXPECT_TRUE(nodes.empty());
    EXPECT_EQ(collector.QueryCurUbCData(ubcs), database::OP_RET::SUCCESS);
    EXPECT_TRUE(ubcs.empty());
    EXPECT_EQ(collector.QueryCurPortData(ports), database::OP_RET::SUCCESS);
    EXPECT_TRUE(ports.empty());
}
