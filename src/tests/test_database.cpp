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

#include <gtest/gtest.h>

#include <sqlite3.h>

#include <chrono>
#include <filesystem>
#include <string>
#include <thread>
#include <vector>

#include "temp_dir.h"
#include "database.h"
#include "logger.h"

namespace database {
// database.cpp 中的内部自由函数（外部链接），直接前向声明进行直测
bool IsSafeIdentifier(const string &identifier);
bool IsValidComparison(COMP_SYMB comparison);
bool IsValidColumnType(const string &type);
} // namespace database

namespace {

// 被测实现中打日志，log4cplus 必须先初始化
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 每用例独立临时目录（公共实现见 temp_dir.h）

// 通用三列表：id 为主键，name 可空
database::TableParams MakeParams()
{
    return {
        std::make_tuple(std::string("id"), std::string("TEXT"), true, true),
        std::make_tuple(std::string("name"), std::string("TEXT"), false, false),
        std::make_tuple(std::string("count"), std::string("INTEGER"), false, false),
    };
}

// 建好表并打开的数据库（不带历史库）；构造函数中只能用 EXPECT（ASSERT 会生成 return 语句）
struct SimpleDb {
    database::Database db;
    explicit SimpleDb(const std::string &path)
    {
        EXPECT_EQ(db.OpenDb(path, false), database::OP_RET::SUCCESS);
        EXPECT_EQ(db.CreateTable("items", MakeParams()), database::OP_RET::SUCCESS);
    }
    ~SimpleDb() { db.Close(); }
};

} // namespace

// ---------------------------------------------------------------------------
// 纯函数直测
// ---------------------------------------------------------------------------

TEST(DatabaseHelpers, IsSafeIdentifier)
{
    EXPECT_TRUE(database::IsSafeIdentifier("abc_123"));
    EXPECT_TRUE(database::IsSafeIdentifier("_x"));
    EXPECT_TRUE(database::IsSafeIdentifier("a1"));
    // 空、数字开头、非法字符均拒绝
    EXPECT_FALSE(database::IsSafeIdentifier(""));
    EXPECT_FALSE(database::IsSafeIdentifier("1abc"));
    EXPECT_FALSE(database::IsSafeIdentifier("a-b"));
    EXPECT_FALSE(database::IsSafeIdentifier("a b"));
}

TEST(DatabaseHelpers, IsValidColumnType)
{
    EXPECT_TRUE(database::IsValidColumnType("TEXT"));
    EXPECT_TRUE(database::IsValidColumnType("INTEGER"));
    EXPECT_TRUE(database::IsValidColumnType("REAL"));
    EXPECT_TRUE(database::IsValidColumnType("BLOB"));
    EXPECT_TRUE(database::IsValidColumnType("NUMERIC"));
    // 类型大小写敏感，未知类型拒绝
    EXPECT_FALSE(database::IsValidColumnType("text"));
    EXPECT_FALSE(database::IsValidColumnType("VARCHAR"));
}

TEST(DatabaseHelpers, IsValidComparison)
{
    EXPECT_TRUE(database::IsValidComparison(database::EQ));
    EXPECT_TRUE(database::IsValidComparison(database::NEQ));
    EXPECT_TRUE(database::IsValidComparison(database::LT));
    EXPECT_TRUE(database::IsValidComparison(database::LE));
    EXPECT_TRUE(database::IsValidComparison(database::GT));
    EXPECT_TRUE(database::IsValidComparison(database::GE));
    EXPECT_TRUE(database::IsValidComparison(database::IN));
    EXPECT_FALSE(database::IsValidComparison(nullptr));
    EXPECT_FALSE(database::IsValidComparison("=="));
}

TEST(DatabaseHelpers, GetNowTimestampMirrorsWallClockWrapped)
{
    // 生产缺陷：GetNowTimestamp 返回 int（32 位），毫秒时间戳（约 1.79e12）溢出为负值
    // （例：1790136491492 包装后为 -864870940），影响 update/expire 时间戳语义。已报告勿修。
    // 这里验证其等于墙钟毫秒按 int 包装后的值（±2ms 容差）；缺陷修复为 64 位后需更新断言。
    auto nowMs = std::chrono::duration_cast<std::chrono::milliseconds>(
                     std::chrono::system_clock::now().time_since_epoch())
                     .count();
    const int wrapped = static_cast<int>(nowMs); // gcc：模 2^32 包装，与生产行为一致
    const int before = database::GetNowTimestamp();
    const int after = database::GetNowTimestamp();
    auto nearWrapped = [wrapped](int v) { return v >= wrapped - 2 && v <= wrapped + 2; };
    EXPECT_TRUE(nearWrapped(before));
    EXPECT_TRUE(nearWrapped(after));
}

// ---------------------------------------------------------------------------
// 打开/关闭
// ---------------------------------------------------------------------------

TEST(DatabaseLifecycle, OpenCreatesFilesAndCloseSucceeds)
{
    TempDir dir;
    const std::string path = std::filesystem::path(dir.Path()).append("test.db").string();
    {
        database::Database db;
        EXPECT_EQ(db.OpenDb(path, false), database::OP_RET::SUCCESS);
        EXPECT_TRUE(std::filesystem::exists(path));
        EXPECT_EQ(db.Close(), database::OP_RET::SUCCESS);
    }
    // 关闭后可再次打开
    database::Database db;
    EXPECT_EQ(db.OpenDb(path, false), database::OP_RET::SUCCESS);
    EXPECT_EQ(db.Close(), database::OP_RET::SUCCESS);
}

TEST(DatabaseLifecycle, OpenWithHistoryCreatesHistoryFile)
{
    TempDir dir;
    const std::string path = std::filesystem::path(dir.Path()).append("his.db").string();
    database::Database db;
    EXPECT_EQ(db.OpenDb(path, true), database::OP_RET::SUCCESS);
    EXPECT_EQ(db.CreateTable("items", MakeParams()), database::OP_RET::SUCCESS);
    EXPECT_TRUE(std::filesystem::exists(path));
    EXPECT_TRUE(std::filesystem::exists(path + "_history"));
    EXPECT_EQ(db.Close(), database::OP_RET::SUCCESS);
}

TEST(DatabaseLifecycle, OpenInvalidPathFails)
{
    // 父目录不存在：sqlite 打开失败
    database::Database db;
    EXPECT_EQ(db.OpenDb("/nonexistent_witty_dir/sub/test.db", false), database::OP_RET::FAIL);
    // 失败后句柄仍可安全关闭
    EXPECT_EQ(db.Close(), database::OP_RET::SUCCESS);
}

// ---------------------------------------------------------------------------
// 建表
// ---------------------------------------------------------------------------

TEST(DatabaseCreateTable, ValidDefinitionRegistersColumns)
{
    TempDir dir;
    database::Database db;
    ASSERT_EQ(db.OpenDb(std::filesystem::path(dir.Path()).append("test.db").string(), false), database::OP_RET::SUCCESS);
    EXPECT_EQ(db.CreateTable("items", MakeParams()), database::OP_RET::SUCCESS);
    // 重复建表（IF NOT EXISTS）仍成功
    EXPECT_EQ(db.CreateTable("items", MakeParams()), database::OP_RET::SUCCESS);
    // 列注册生效：可用全部列名插入/查询
    database::DataMap row = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    EXPECT_EQ(db.InsertData("items", row), database::OP_RET::SUCCESS);
    database::QueryResult res;
    ASSERT_EQ(db.QueryCurrData("items", {}, &res), database::OP_RET::SUCCESS);
    ASSERT_EQ(res.size(), 1u);
    EXPECT_EQ(res[0]["id"], "a");
    db.Close();
}

TEST(DatabaseCreateTable, RejectsInvalidDefinitions)
{
    TempDir dir;
    database::Database db;
    ASSERT_EQ(db.OpenDb(std::filesystem::path(dir.Path()).append("test.db").string(), false), database::OP_RET::SUCCESS);
    // 空列定义
    EXPECT_EQ(db.CreateTable("items", {}), database::OP_RET::FAIL);
    // 非法表名
    EXPECT_EQ(db.CreateTable("1bad", MakeParams()), database::OP_RET::FAIL);
    EXPECT_EQ(db.CreateTable("bad-name", MakeParams()), database::OP_RET::FAIL);
    // 非法列名
    database::TableParams badCol = {std::make_tuple(std::string("id!"), std::string("TEXT"), false, false)};
    EXPECT_EQ(db.CreateTable("items", badCol), database::OP_RET::FAIL);
    // 非法列类型
    database::TableParams badType = {std::make_tuple(std::string("id"), std::string("varchar"), false, false)};
    EXPECT_EQ(db.CreateTable("items", badType), database::OP_RET::FAIL);
    // 保留列名冲突
    database::TableParams reserved = {std::make_tuple(std::string("update_timestamp"), std::string("INTEGER"),
                                                      false, false)};
    EXPECT_EQ(db.CreateTable("items", reserved), database::OP_RET::FAIL);
    database::TableParams reserved2 = {std::make_tuple(std::string("expire_timestamp"), std::string("INTEGER"),
                                                       false, false)};
    EXPECT_EQ(db.CreateTable("items", reserved2), database::OP_RET::FAIL);
    // 重复列名
    database::TableParams dup = {std::make_tuple(std::string("id"), std::string("TEXT"), false, false),
                                 std::make_tuple(std::string("id"), std::string("TEXT"), false, false)};
    EXPECT_EQ(db.CreateTable("items", dup), database::OP_RET::FAIL);
    db.Close();
}

// ---------------------------------------------------------------------------
// 插入与查询
// ---------------------------------------------------------------------------

TEST(DatabaseInsertQuery, InsertAndQueryAll)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    database::DataMap row1 = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    database::DataMap row2 = {{"id", "b"}, {"name", "beta"}, {"count", "2"}};
    EXPECT_EQ(simple.db.InsertData("items", row1), database::OP_RET::SUCCESS);
    EXPECT_EQ(simple.db.InsertData("items", row2), database::OP_RET::SUCCESS);

    database::QueryResult res;
    ASSERT_EQ(simple.db.QueryCurrData("items", {}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(res.size(), 2u);
    // 结果按主键排序后核对
    ASSERT_EQ(res[0]["id"], "a");
    EXPECT_EQ(res[0]["name"], "alpha");
    ASSERT_EQ(res[1]["id"], "b");
    EXPECT_EQ(res[1]["count"], "2");
}

TEST(DatabaseInsertQuery, InsertWithDuplicatePrimaryKeyUpdates)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    database::DataMap row = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    ASSERT_EQ(simple.db.InsertData("items", row), database::OP_RET::SUCCESS);

    // 相同主键再次插入：转为更新
    database::DataMap again = {{"id", "a"}, {"name", "alpha2"}, {"count", "9"}};
    EXPECT_EQ(simple.db.InsertData("items", again), database::OP_RET::SUCCESS);

    database::QueryResult res;
    ASSERT_EQ(simple.db.QueryCurrData("items", {}, &res), database::OP_RET::SUCCESS);
    ASSERT_EQ(res.size(), 1u);
    EXPECT_EQ(res[0]["name"], "alpha2");
    EXPECT_EQ(res[0]["count"], "9");
}

TEST(DatabaseInsertQuery, InsertRejectsInvalidTableAndColumn)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    database::DataMap row = {{"id", "a"}};
    // 未注册的表
    EXPECT_EQ(simple.db.InsertData("ghost", row), database::OP_RET::FAIL);
    // 未注册的列
    database::DataMap badCol = {{"id", "a"}, {"no_such_col", "v"}};
    EXPECT_EQ(simple.db.InsertData("items", badCol), database::OP_RET::FAIL);
}

TEST(DatabaseInsertQuery, NullColumnsReadAsNullString)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    // 只插主键：其余可空列为 SQL NULL，查询时表示为 "NULL"
    database::DataMap row = {{"id", "n"}};
    ASSERT_EQ(simple.db.InsertData("items", row), database::OP_RET::SUCCESS);
    database::QueryResult res;
    ASSERT_EQ(simple.db.QueryCurrData("items", {}, &res), database::OP_RET::SUCCESS);
    ASSERT_EQ(res.size(), 1u);
    EXPECT_EQ(res[0]["name"], "NULL");
    EXPECT_EQ(res[0]["count"], "NULL");
}

TEST(DatabaseInsertQuery, QueryWithAllComparisonOperators)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    database::DataMap row1 = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    database::DataMap row2 = {{"id", "b"}, {"name", "beta"}, {"count", "2"}};
    ASSERT_EQ(simple.db.InsertData("items", row1), database::OP_RET::SUCCESS);
    ASSERT_EQ(simple.db.InsertData("items", row2), database::OP_RET::SUCCESS);

    database::QueryResult res;
    // EQ
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"id", {database::EQ, "a"}}}, &res), database::OP_RET::SUCCESS);
    ASSERT_EQ(res.size(), 1u);
    EXPECT_EQ(res[0]["id"], "a");
    // NEQ
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"id", {database::NEQ, "a"}}}, &res), database::OP_RET::SUCCESS);
    ASSERT_EQ(res.size(), 1u);
    EXPECT_EQ(res[0]["id"], "b");
    // LT / LE
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"count", {database::LT, "2"}}}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(res.size(), 1u);
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"count", {database::LE, "2"}}}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(res.size(), 2u);
    // GT / GE
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"count", {database::GT, "1"}}}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(res.size(), 1u);
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"count", {database::GE, "1"}}}, &res), database::OP_RET::SUCCESS);
    EXPECT_EQ(res.size(), 2u);
    // IN（实现为 IS NOT）
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"count", {database::IN, "1"}}}, &res), database::OP_RET::SUCCESS);
    ASSERT_EQ(res.size(), 1u);
    EXPECT_EQ(res[0]["id"], "b");
    // 多条件 AND
    ASSERT_EQ(simple.db.QueryCurrData("items", {{"id", {database::EQ, "b"}}, {"count", {database::EQ, "2"}}}, &res),
              database::OP_RET::SUCCESS);
    EXPECT_EQ(res.size(), 1u);
}

TEST(DatabaseInsertQuery, QueryRejectsInvalidInputs)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    database::QueryResult res;
    // 未注册表
    EXPECT_EQ(simple.db.QueryCurrData("ghost", {}, &res), database::OP_RET::FAIL);
    EXPECT_TRUE(res.empty());
    // 未注册列
    EXPECT_EQ(simple.db.QueryCurrData("items", {{"no_such_col", {database::EQ, "1"}}}, &res),
              database::OP_RET::FAIL);
    // 非法比较符
    EXPECT_EQ(simple.db.QueryCurrData("items", {{"count", {"==", "1"}}}, &res), database::OP_RET::FAIL);
}

// ---------------------------------------------------------------------------
// 更新
// ---------------------------------------------------------------------------

TEST(DatabaseUpdate, UpdatesMatchingRows)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    database::DataMap row1 = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    database::DataMap row2 = {{"id", "b"}, {"name", "beta"}, {"count", "1"}};
    ASSERT_EQ(simple.db.InsertData("items", row1), database::OP_RET::SUCCESS);
    ASSERT_EQ(simple.db.InsertData("items", row2), database::OP_RET::SUCCESS);

    // 按非主键列条件更新
    database::ConditionMap cond = {{"count", {database::EQ, "1"}}};
    database::DataMap content = {{"count", "100"}};
    EXPECT_EQ(simple.db.UpdateData("items", cond, content), database::OP_RET::SUCCESS);

    database::QueryResult res;
    ASSERT_EQ(simple.db.QueryCurrData("items", {}, &res), database::OP_RET::SUCCESS);
    ASSERT_EQ(res.size(), 2u);
    EXPECT_EQ(res[0]["count"], "100");
    EXPECT_EQ(res[1]["count"], "100");
}

TEST(DatabaseUpdate, RejectsInvalidInputs)
{
    TempDir dir;
    SimpleDb simple(std::filesystem::path(dir.Path()).append("test.db").string());
    database::DataMap row = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    ASSERT_EQ(simple.db.InsertData("items", row), database::OP_RET::SUCCESS);

    // 未注册表
    database::ConditionMap cond = {{"id", {database::EQ, "a"}}};
    EXPECT_EQ(simple.db.UpdateData("ghost", cond, {{"count", "2"}}), database::OP_RET::FAIL);
    // 空条件
    EXPECT_EQ(simple.db.UpdateData("items", {}, {{"count", "2"}}), database::OP_RET::FAIL);
    // 未注册列
    EXPECT_EQ(simple.db.UpdateData("items", cond, {{"no_such_col", "2"}}), database::OP_RET::FAIL);
    // 条件中未注册列
    database::ConditionMap badCond = {{"no_such_col", {database::EQ, "x"}}};
    EXPECT_EQ(simple.db.UpdateData("items", badCond, {{"count", "2"}}), database::OP_RET::FAIL);
}

// ---------------------------------------------------------------------------
// 删除与历史库
// ---------------------------------------------------------------------------

TEST(DatabaseHistory, DeleteExpiresHistoryRows)
{
    TempDir dir;
    database::Database db;
    ASSERT_EQ(db.OpenDb(std::filesystem::path(dir.Path()).append("his.db").string(), true), database::OP_RET::SUCCESS);
    ASSERT_EQ(db.CreateTable("items", MakeParams()), database::OP_RET::SUCCESS);

    database::DataMap row = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    ASSERT_EQ(db.InsertData("items", row), database::OP_RET::SUCCESS);

    const int before = database::GetNowTimestamp();
    // 当前库与历史库中均能查到该行
    database::QueryResult curr;
    ASSERT_EQ(db.QueryCurrData("items", {}, &curr), database::OP_RET::SUCCESS);
    ASSERT_EQ(curr.size(), 1u);
    database::QueryResult his;
    ASSERT_EQ(db.QueryHisData("items", {}, &his, before - 60000, before + 60000), database::OP_RET::SUCCESS);
    ASSERT_EQ(his.size(), 1u);

    // 删除：当前库移除，历史库置过期
    database::ConditionMap cond = {{"id", {database::EQ, "a"}}};
    const int deletedAt = database::GetNowTimestamp();
    EXPECT_EQ(db.DeleteData("items", cond), database::OP_RET::SUCCESS);

    ASSERT_EQ(db.QueryCurrData("items", {}, &curr), database::OP_RET::SUCCESS);
    EXPECT_TRUE(curr.empty());

    // 历史窗口覆盖删除时刻：行仍可见（expire >= start）
    ASSERT_EQ(db.QueryHisData("items", {}, &his, deletedAt - 60000, deletedAt + 60000), database::OP_RET::SUCCESS);
    EXPECT_EQ(his.size(), 1u);
    // 历史窗口完全在删除之后：行不可见（expire < start）
    ASSERT_EQ(db.QueryHisData("items", {}, &his, deletedAt + 10000, deletedAt + 20000), database::OP_RET::SUCCESS);
    EXPECT_TRUE(his.empty());

    // DeleteData 的异常入参
    EXPECT_EQ(db.DeleteData("items", {}), database::OP_RET::FAIL);
    EXPECT_EQ(db.DeleteData("ghost", cond), database::OP_RET::FAIL);
    db.Close();
}

TEST(DatabaseHistory, UpdateAppendsHistoryRow)
{
    TempDir dir;
    database::Database db;
    ASSERT_EQ(db.OpenDb(std::filesystem::path(dir.Path()).append("his.db").string(), true), database::OP_RET::SUCCESS);
    ASSERT_EQ(db.CreateTable("items", MakeParams()), database::OP_RET::SUCCESS);

    database::DataMap row = {{"id", "a"}, {"name", "alpha"}, {"count", "1"}};
    ASSERT_EQ(db.InsertData("items", row), database::OP_RET::SUCCESS);

    // 生产缺陷：历史表以 (id, update_timestamp) 为唯一键，而时间戳只有毫秒精度——
    // 同一毫秒内对同一 key 先插入再更新必然触发 UNIQUE 冲突导致 UpdateData 失败
    // （间歇复现）。已报告勿修；测试休眠 2ms 跨毫秒以稳定走通成功路径。
    std::this_thread::sleep_for(std::chrono::milliseconds(2));

    // 更新后历史库追加一条新版本
    database::ConditionMap cond = {{"id", {database::EQ, "a"}}};
    const int now = database::GetNowTimestamp();
    ASSERT_EQ(db.UpdateData("items", cond, {{"count", "5"}}), database::OP_RET::SUCCESS);

    database::QueryResult his;
    ASSERT_EQ(db.QueryHisData("items", cond, &his, now - 60000, now + 60000), database::OP_RET::SUCCESS);
    // 旧版本（expire 被打上）与新版本（expire 为 NULL）都在窗口内
    EXPECT_EQ(his.size(), 2u);

    // 带条件的当前库查询
    database::QueryResult curr;
    ASSERT_EQ(db.QueryCurrData("items", cond, &curr), database::OP_RET::SUCCESS);
    ASSERT_EQ(curr.size(), 1u);
    EXPECT_EQ(curr[0]["count"], "5");
    db.Close();
}

TEST(DatabaseHistory, QueryHisDataRejectsUnknownTable)
{
    TempDir dir;
    database::Database db;
    ASSERT_EQ(db.OpenDb(std::filesystem::path(dir.Path()).append("his.db").string(), true), database::OP_RET::SUCCESS);
    ASSERT_EQ(db.CreateTable("items", MakeParams()), database::OP_RET::SUCCESS);
    database::QueryResult res;
    EXPECT_EQ(db.QueryHisData("ghost", {}, &res, 0, 1000), database::OP_RET::FAIL);
    db.Close();
}
