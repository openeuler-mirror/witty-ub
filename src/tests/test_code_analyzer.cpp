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

// B3 B 级：code_analyzer 库——自由函数（Base64/会话路径/消息挑选）与
// 参数解析/prompt 构造。Start() 仅测无网络的失败路径（组件缺失、回环拒绝端口连接）。

#include <gtest/gtest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include <json/json.h>

#include "logger.h"
#include "temp_dir.h"
#include "ubse_context.h"

// rack_http 类型（rack_http 经 code_analyzer PUBLIC 链接传递 include 路径）
#include "http/rack_http_types.h"

// 访问 CodeAnalyzer 私有解析/prompt 方法（本仓库既有测试模式）
#define private public
#include "code_analyzer.h"
#undef private

namespace {
// 打日志的库必须先初始化 log4cplus，否则 SEGFAULT
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// RAII 临时目录（公共实现见 temp_dir.h）

// opencode 连接测试端口常量
constexpr int OPENCODE_TEST_PORT = 4096; // FullArgs 默认端口（字符串形式）
constexpr int PARTIAL_NUMERIC_PORT = 12; // "12abc" 经 stoi 前缀解析得到的端口

// 测试用消息时间戳（ms）：值本身无业务含义，仅保证相对先后
constexpr Json::Int64 MSG_TS_1 = 100;
constexpr Json::Int64 MSG_TS_2 = 150;
constexpr Json::Int64 MSG_TS_3 = 200;
constexpr Json::Int64 MSG_TS_4 = 250;
constexpr Json::Int64 MSG_TS_5 = 300;
constexpr Json::Int64 MSG_TS_6 = 500;
constexpr Json::Int64 MSG_TS_SAMPLE = 1234;

// 全量覆盖单例 argMap（GetArgMap 返回 const 引用，对象本身非 const，const_cast 安全）
void SetArgMap(std::unordered_map<std::string, std::string> m)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    const_cast<std::unordered_map<std::string, std::string> &>(ctx.GetArgMap()) = std::move(m);
}

// 构造一条消息 JSON
Json::Value MakeMessage(const std::string &role, Json::Int64 created)
{
    Json::Value msg;
    msg["info"]["role"] = role;
    msg["info"]["time"]["created"] = created;
    return msg;
}

// 全量合法 argMap（回环不可达端口，仅用于解析成功路径）
std::unordered_map<std::string, std::string> FullArgs(const std::string &port = "4096")
{
    return {{"opencode-url", "http://127.0.0.1"},   {"opencode-port", port},
            {"opencode-username", "user-1"},        {"opencode-passwd", "pass-1"},
            {"ubsocket-src-path", "/src/ubsocket"}, {"umq-src-path", "/src/umq"},
            {"liburma-src-path", "/src/liburma"},   {"libudma-src-path", "/src/libudma"}};
}
} // namespace

// 测试文件内补充声明 cpp 中的外部链接自由函数
namespace code_analyzer {
Json::Int64 GetCurrentTimeMs();
Json::Int64 GetMessageCreatedTimeMs(const Json::Value &message);
const Json::Value *FindPreferredAssistantMessage(const Json::Value &messages, Json::Int64 promptSubmittedAtMs);
std::string BuildSessionPath(const std::string &pathTemplate, const std::string &sessionId);
std::string Base64Encode(const std::string &input);
void ApplyBasicAuthHeader(rack::com::RackHttpRequest &req, const OpencodeConnection &conn);
bool StringToJson(Json::Value &root, const std::string &jsonStr);
} // namespace code_analyzer

// ---------------------------------------------------------------------------
// Base64Encode：RFC 4648 标准向量
// ---------------------------------------------------------------------------
TEST(Base64EncodeTest, StandardVectors)
{
    EXPECT_EQ(code_analyzer::Base64Encode(""), "");
    EXPECT_EQ(code_analyzer::Base64Encode("f"), "Zg==");
    EXPECT_EQ(code_analyzer::Base64Encode("fo"), "Zm8=");
    EXPECT_EQ(code_analyzer::Base64Encode("foo"), "Zm9v");
    EXPECT_EQ(code_analyzer::Base64Encode("foob"), "Zm9vYg==");
    EXPECT_EQ(code_analyzer::Base64Encode("fooba"), "Zm9vYmE=");
    EXPECT_EQ(code_analyzer::Base64Encode("foobar"), "Zm9vYmFy");
}

// 二进制字节：0x00/0xff 等不做特殊处理
TEST(Base64EncodeTest, BinaryBytes)
{
    const std::string bin{static_cast<char>(0x00), static_cast<char>(0x01), static_cast<char>(0x02),
                          static_cast<char>(0xff)};
    EXPECT_EQ(code_analyzer::Base64Encode(bin), "AAEC/w==");
}

// ---------------------------------------------------------------------------
// GetMessageCreatedTimeMs / FindPreferredAssistantMessage
// ---------------------------------------------------------------------------
TEST(AssistantMessageTest, CreatedTimeMissingFormsReturnZero)
{
    Json::Value empty;
    EXPECT_EQ(code_analyzer::GetMessageCreatedTimeMs(empty), 0);

    Json::Value noTime;
    noTime["info"]["role"] = "assistant";
    EXPECT_EQ(code_analyzer::GetMessageCreatedTimeMs(noTime), 0);

    Json::Value timeNotObj;
    timeNotObj["info"]["time"] = "bad";
    EXPECT_EQ(code_analyzer::GetMessageCreatedTimeMs(timeNotObj), 0);

    Json::Value ok = MakeMessage("assistant", MSG_TS_SAMPLE);
    EXPECT_EQ(code_analyzer::GetMessageCreatedTimeMs(ok), MSG_TS_SAMPLE);
}

TEST(AssistantMessageTest, EmptyOrNullptrWhenNoAssistant)
{
    Json::Value emptyArr(Json::arrayValue);
    EXPECT_EQ(code_analyzer::FindPreferredAssistantMessage(emptyArr, 0), nullptr);

    Json::Value onlyUser(Json::arrayValue);
    onlyUser.append(MakeMessage("user", MSG_TS_1));
    EXPECT_EQ(code_analyzer::FindPreferredAssistantMessage(onlyUser, 0), nullptr);
}

TEST(AssistantMessageTest, FallsBackToLatestOlderAssistant)
{
    Json::Value arr(Json::arrayValue);
    arr.append(MakeMessage("assistant", MSG_TS_1));
    arr.append(MakeMessage("assistant", MSG_TS_3));
    const Json::Value *res = code_analyzer::FindPreferredAssistantMessage(arr, MSG_TS_6);
    ASSERT_NE(res, nullptr);
    EXPECT_EQ((*res)["info"]["time"]["created"].asInt64(), MSG_TS_3);
}

TEST(AssistantMessageTest, PrefersReplyAfterPromptSubmission)
{
    Json::Value arr(Json::arrayValue);
    arr.append(MakeMessage("user", MSG_TS_1));
    arr.append(MakeMessage("assistant", MSG_TS_2)); // 提交前的旧回复
    arr.append(MakeMessage("assistant", MSG_TS_5)); // 提交后的新回复
    arr.append(MakeMessage("assistant", MSG_TS_4)); // 提交后但更早
    const Json::Value *res = code_analyzer::FindPreferredAssistantMessage(arr, MSG_TS_3);
    ASSERT_NE(res, nullptr);
    EXPECT_EQ((*res)["info"]["time"]["created"].asInt64(), MSG_TS_5);
}

TEST(AssistantMessageTest, EqualTimestampsLaterWins)
{
    // >= 比较：created 相同时后出现的胜出
    Json::Value arr(Json::arrayValue);
    arr.append(MakeMessage("assistant", MSG_TS_1));
    Json::Value second = MakeMessage("assistant", MSG_TS_1);
    second["tag"] = "second";
    arr.append(second);
    const Json::Value *res = code_analyzer::FindPreferredAssistantMessage(arr, MSG_TS_3);
    ASSERT_NE(res, nullptr);
    EXPECT_EQ((*res)["tag"].asString(), "second");
}

// ---------------------------------------------------------------------------
// BuildSessionPath
// ---------------------------------------------------------------------------
TEST(BuildSessionPathTest, ReplacesPlaceholder)
{
    EXPECT_EQ(code_analyzer::BuildSessionPath("/session/:id/message", "abc"), "/session/abc/message");
    EXPECT_EQ(code_analyzer::BuildSessionPath("/session/:id/prompt", "s-1"), "/session/s-1/prompt");
}

TEST(BuildSessionPathTest, KeepsPathWithoutPlaceholder)
{
    EXPECT_EQ(code_analyzer::BuildSessionPath("/session/list", "abc"), "/session/list");
}

// ---------------------------------------------------------------------------
// ApplyBasicAuthHeader
// ---------------------------------------------------------------------------
TEST(BasicAuthTest, NoHeaderWithoutPassword)
{
    rack::com::RackHttpRequest req;
    code_analyzer::OpencodeConnection conn;
    conn.url = "http://127.0.0.1";
    conn.port = 4096;
    // passwd 为空 optional
    code_analyzer::ApplyBasicAuthHeader(req, conn);
    EXPECT_EQ(req.headers.count("Authorization"), 0u);

    // passwd 为空串
    conn.passwd = "";
    code_analyzer::ApplyBasicAuthHeader(req, conn);
    EXPECT_EQ(req.headers.count("Authorization"), 0u);
}

TEST(BasicAuthTest, DefaultUsernameWhenMissing)
{
    rack::com::RackHttpRequest req;
    code_analyzer::OpencodeConnection conn;
    conn.passwd = "pw";
    // username 缺省 -> "opencode"
    code_analyzer::ApplyBasicAuthHeader(req, conn);
    EXPECT_EQ(req.headers["Authorization"], "Basic " + code_analyzer::Base64Encode("opencode:pw"));

    // username 为空串 -> 同样回退默认
    rack::com::RackHttpRequest req2;
    conn.username = "";
    code_analyzer::ApplyBasicAuthHeader(req2, conn);
    EXPECT_EQ(req2.headers["Authorization"], "Basic " + code_analyzer::Base64Encode("opencode:pw"));
}

TEST(BasicAuthTest, CustomUsernameAndPassword)
{
    rack::com::RackHttpRequest req;
    code_analyzer::OpencodeConnection conn;
    conn.username = "alice";
    conn.passwd = "secret";
    code_analyzer::ApplyBasicAuthHeader(req, conn);
    EXPECT_EQ(req.headers["Authorization"], "Basic " + code_analyzer::Base64Encode("alice:secret"));
}

// ---------------------------------------------------------------------------
// StringToJson / GetCurrentTimeMs
// ---------------------------------------------------------------------------
TEST(JsonUtilTest, StringToJsonParsesAndRejects)
{
    Json::Value root;
    EXPECT_TRUE(code_analyzer::StringToJson(root, "{\"a\":1}"));
    EXPECT_EQ(root["a"].asInt(), 1);
    EXPECT_FALSE(code_analyzer::StringToJson(root, "not-a-json"));
}

TEST(JsonUtilTest, CurrentTimeMsIsNearNow)
{
    const auto before = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::system_clock::now().time_since_epoch()).count();
    const auto now = code_analyzer::GetCurrentTimeMs();
    const auto after = std::chrono::duration_cast<std::chrono::milliseconds>(
                           std::chrono::system_clock::now().time_since_epoch()).count();
    EXPECT_GE(now, before);
    EXPECT_LE(now, after);
}

// ---------------------------------------------------------------------------
// CodeAnalyzer 私有：连接参数解析
// ---------------------------------------------------------------------------
class CodeAnalyzerParse : public ::testing::Test {
protected:
    code_analyzer::CodeAnalyzer analyzer;

    void SetUp() override { SetArgMap({}); }
};

TEST_F(CodeAnalyzerParse, MissingUrlFails)
{
    EXPECT_EQ(analyzer.ParseOpencodeConn({{"opencode-port", "4096"}}), RACK_FAIL);
}

TEST_F(CodeAnalyzerParse, MissingPortFails)
{
    EXPECT_EQ(analyzer.ParseOpencodeConn({{"opencode-url", "http://127.0.0.1"}}), RACK_FAIL);
}

TEST_F(CodeAnalyzerParse, NonNumericPortFails)
{
    EXPECT_EQ(analyzer.ParseOpencodeConn({{"opencode-url", "http://127.0.0.1"}, {"opencode-port", "abc"}}), RACK_FAIL);
}

TEST_F(CodeAnalyzerParse, FullArgumentsFillConnection)
{
    EXPECT_EQ(analyzer.ParseOpencodeConn(FullArgs()), RACK_OK);
    EXPECT_EQ(analyzer.conn_.url, "http://127.0.0.1");
    EXPECT_EQ(analyzer.conn_.port, OPENCODE_TEST_PORT);
    ASSERT_TRUE(analyzer.conn_.username.has_value());
    EXPECT_EQ(analyzer.conn_.username.value(), "user-1");
    ASSERT_TRUE(analyzer.conn_.passwd.has_value());
    EXPECT_EQ(analyzer.conn_.passwd.value(), "pass-1");
}

// stoi 的前缀解析行为："12abc" 解析为 12 而不抛异常
TEST_F(CodeAnalyzerParse, PartialNumericPortIsAcceptedByStoi)
{
    EXPECT_EQ(analyzer.ParseOpencodeConn({{"opencode-url", "http://127.0.0.1"}, {"opencode-port", "12abc"}}), RACK_OK);
    EXPECT_EQ(analyzer.conn_.port, PARTIAL_NUMERIC_PORT);
}

TEST_F(CodeAnalyzerParse, UsernameFallsBackToEmptyOptional)
{
    auto args = FullArgs();
    args.erase("opencode-username");
    EXPECT_EQ(analyzer.ParseOpencodeConn(args), RACK_OK);
    EXPECT_FALSE(analyzer.conn_.username.has_value());

    // 空串用户名同样保持空 optional
    code_analyzer::CodeAnalyzer a2;
    auto args2 = FullArgs();
    args2["opencode-username"] = "";
    EXPECT_EQ(a2.ParseOpencodeConn(args2), RACK_OK);
    EXPECT_FALSE(a2.conn_.username.has_value());
}

TEST_F(CodeAnalyzerParse, MissingPasswordKeepsOptionalEmpty)
{
    auto args = FullArgs();
    args.erase("opencode-passwd");
    EXPECT_EQ(analyzer.ParseOpencodeConn(args), RACK_OK);
    EXPECT_FALSE(analyzer.conn_.passwd.has_value());

    // 空串密码：有值但为空（后续 ApplyBasicAuthHeader 不加头）
    code_analyzer::CodeAnalyzer a2;
    auto args2 = FullArgs();
    args2["opencode-passwd"] = "";
    EXPECT_EQ(a2.ParseOpencodeConn(args2), RACK_OK);
    ASSERT_TRUE(a2.conn_.passwd.has_value());
    EXPECT_TRUE(a2.conn_.passwd->empty());
}

// ---------------------------------------------------------------------------
// CodeAnalyzer 私有：源码路径 / compile_commands 解析
// ---------------------------------------------------------------------------
TEST_F(CodeAnalyzerParse, SrcPathMissingAnyComponentFails)
{
    EXPECT_EQ(analyzer.ParseSrcPath({{"ubsocket-src-path", "/a"}, {"liburma-src-path", "/c"},
                                     {"libudma-src-path", "/d"}}),
              RACK_FAIL); // 缺 umq
}

TEST_F(CodeAnalyzerParse, SrcPathFullArgumentsFillMap)
{
    EXPECT_EQ(analyzer.ParseSrcPath(FullArgs()), RACK_OK);
    EXPECT_EQ(analyzer.input_.componentsPaths.size(), 4u);
    EXPECT_EQ(analyzer.input_.componentsPaths["ubsocket"], "/src/ubsocket");
    EXPECT_EQ(analyzer.input_.componentsPaths["umq"], "/src/umq");
    EXPECT_EQ(analyzer.input_.componentsPaths["liburma"], "/src/liburma");
    EXPECT_EQ(analyzer.input_.componentsPaths["libudma"], "/src/libudma");
}

TEST_F(CodeAnalyzerParse, CompileCommandsPrefersExplicitArgument)
{
    analyzer.input_.componentsPaths["umq"] = "/src/umq";
    EXPECT_EQ(analyzer.ParseCompileCommandsPath({{"umq-compile-commands-path", "/explicit/cc.json"}}), RACK_OK);
    EXPECT_EQ(analyzer.input_.compileCommandsPaths["umq"], "/explicit/cc.json");
}

TEST_F(CodeAnalyzerParse, CompileCommandsGuessesFromExistingFile)
{
    TempDir dir;
    const auto cc = dir.Path() / "compile_commands.json";
    {
        std::ofstream out(cc);
        out << "[]";
    }
    analyzer.input_.componentsPaths["umq"] = dir.Path().string();
    EXPECT_EQ(analyzer.ParseCompileCommandsPath({}), RACK_OK);
    EXPECT_EQ(analyzer.input_.compileCommandsPaths["umq"], cc.string());
}

TEST_F(CodeAnalyzerParse, CompileCommandsSkipsWhenFileMissing)
{
    TempDir dir;
    analyzer.input_.componentsPaths["umq"] = (dir.Path() / "nope").string();
    EXPECT_EQ(analyzer.ParseCompileCommandsPath({}), RACK_OK);
    EXPECT_EQ(analyzer.input_.compileCommandsPaths.count("umq"), 0u);
}

TEST_F(CodeAnalyzerParse, CompileCommandsSkipsComponentWithoutSrc)
{
    EXPECT_EQ(analyzer.ParseCompileCommandsPath({}), RACK_OK);
    EXPECT_TRUE(analyzer.input_.compileCommandsPaths.empty());
}

// ---------------------------------------------------------------------------
// CodeAnalyzer 私有：prompt 构造
// ---------------------------------------------------------------------------
TEST_F(CodeAnalyzerParse, AnalyzerPromptEmptyForUnknownComponent)
{
    EXPECT_TRUE(analyzer.BuildAnalyzerSkillPrompt("skill", analyzer.input_, "nosuch").empty());
}

TEST_F(CodeAnalyzerParse, AnalyzerPromptContainsComponentAndPaths)
{
    analyzer.input_.componentsPaths["umq"] = "/src/umq";
    analyzer.input_.compileCommandsPaths["umq"] = "/cc/umq.json";
    const std::string p = analyzer.BuildAnalyzerSkillPrompt("my-skill", analyzer.input_, "umq");
    EXPECT_NE(p.find("my-skill"), std::string::npos);
    EXPECT_NE(p.find("component: umq"), std::string::npos);
    EXPECT_NE(p.find("source_path: /src/umq"), std::string::npos);
    EXPECT_NE(p.find("compile_commands_path: /cc/umq.json"), std::string::npos);

    // 无 compile_commands 时省略该行
    analyzer.input_.compileCommandsPaths.clear();
    const std::string p2 = analyzer.BuildAnalyzerSkillPrompt("my-skill", analyzer.input_, "umq");
    EXPECT_EQ(p2.find("compile_commands_path"), std::string::npos);
}

TEST_F(CodeAnalyzerParse, AggregationPromptEmptyWhenAnyComponentMissing)
{
    analyzer.input_.componentsPaths["ubsocket"] = "/src/ubsocket";
    EXPECT_TRUE(analyzer.BuildAggregationSkillPrompt("skill", analyzer.input_).empty());
}

TEST_F(CodeAnalyzerParse, AggregationPromptListsAllComponents)
{
    for (const char *c : {"ubsocket", "umq", "liburma", "libudma"}) {
        analyzer.input_.componentsPaths[c] = std::string("/src/") + c;
    }
    const std::string p = analyzer.BuildAggregationSkillPrompt("agg-skill", analyzer.input_);
    EXPECT_NE(p.find("agg-skill"), std::string::npos);
    EXPECT_NE(p.find("--ubsocket-src: /src/ubsocket"), std::string::npos);
    EXPECT_NE(p.find("--umq-src: /src/umq"), std::string::npos);
    EXPECT_NE(p.find("--liburma-src: /src/liburma"), std::string::npos);
    EXPECT_NE(p.find("--libudma-src: /src/libudma"), std::string::npos);
    EXPECT_NE(p.find("overall_callstack.json"), std::string::npos);
}

TEST_F(CodeAnalyzerParse, KeyfuncPromptRequiresUmq)
{
    EXPECT_TRUE(analyzer.BuildKeyfuncSkillPrompt("skill", analyzer.input_).empty());

    analyzer.input_.componentsPaths["umq"] = "/src/umq";
    const std::string p = analyzer.BuildKeyfuncSkillPrompt("kf-skill", analyzer.input_);
    EXPECT_NE(p.find("kf-skill"), std::string::npos);
    EXPECT_NE(p.find("source_path: /src/umq"), std::string::npos);
    EXPECT_NE(p.find("keywords: bind,unbind,post,poll"), std::string::npos);
}

// ---------------------------------------------------------------------------
// Initialize / Start
// ---------------------------------------------------------------------------
TEST(CodeAnalyzerLifecycle, InitializeFailsWithoutArguments)
{
    SetArgMap({});
    code_analyzer::CodeAnalyzer analyzer;
    EXPECT_EQ(analyzer.Initialize(), RACK_FAIL);
}

TEST(CodeAnalyzerLifecycle, InitializeSucceedsWithFullArguments)
{
    SetArgMap(FullArgs());
    code_analyzer::CodeAnalyzer analyzer;
    EXPECT_EQ(analyzer.Initialize(), RACK_OK);
    EXPECT_EQ(analyzer.conn_.port, OPENCODE_TEST_PORT);
    EXPECT_EQ(analyzer.input_.componentsPaths.size(), 4u);

    analyzer.Stop();
    analyzer.UnInitialize();
}

// Start：input_ 为空时组件缺失，直接失败，不发起任何网络请求
TEST(CodeAnalyzerLifecycle, StartFailsWhenComponentMissing)
{
    SetArgMap(FullArgs());
    code_analyzer::CodeAnalyzer analyzer;
    EXPECT_EQ(analyzer.Initialize(), RACK_OK);
    analyzer.input_.componentsPaths.clear();
    EXPECT_EQ(analyzer.Start(), RACK_FAIL);
}

// Start：连接回环拒绝端口（127.0.0.1:1 无监听），CreateSession 快速失败
TEST(CodeAnalyzerLifecycle, StartFailsFastOnUnreachableOpencode)
{
    SetArgMap(FullArgs("1"));
    code_analyzer::CodeAnalyzer analyzer;
    ASSERT_EQ(analyzer.Initialize(), RACK_OK);
    // 连接立即被拒绝（不起服务、不监听端口）
    EXPECT_EQ(analyzer.Start(), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// B5-3 追加：fake opencode 服务驱动的会话/消息 HTTP 路径 + CodeAnalyzerModule
// 覆盖 CreateSession / WaitForSessionVisible / SendMessageAsync /
// WaitForAssistantMessageCompleted / FetchLatestAssistantMessage / Run 的
// 成功与各类失败分支（此前这些方法 0 覆盖或仅连接失败路径）。
// ---------------------------------------------------------------------------

#include <thread>

#include "httplib.h"

#define private public
#include "code_analyzer_module.h"
#undef private

namespace {

// fake 服务启动轮询与 HTTP 状态码
constexpr int SERVER_START_ROUNDS = 400;
constexpr int SERVER_POLL_INTERVAL_MS = 5;
constexpr int HTTP_OK = 200;
constexpr int HTTP_NO_CONTENT = 204;
constexpr int HTTP_NOT_FOUND = 404;
constexpr int HTTP_SERVER_ERROR = 500;

// 本地模拟 opencode：会话创建/查询、异步 prompt、消息拉取
class FakeOpencodeServer {
public:
    FakeOpencodeServer()
    {
        svr_.Post("/session", [this](const httplib::Request &, httplib::Response &res) {
            std::lock_guard<std::mutex> lock(mtx_);
            res.status = sessionPostStatus_;
            res.set_content(sessionPostBody_, "application/json");
        });
        // WaitForSessionVisible 轮询的是 OPENCODE_PATH_SESSION（"/session"，无 :id
        // 占位符，BuildSessionPath 原样返回），因此可见性探测打在 /session 上。
        svr_.Get("/session", [this](const httplib::Request &, httplib::Response &res) {
            std::lock_guard<std::mutex> lock(mtx_);
            res.status = sessionGetStatus_;
            res.set_content(R"([{"id":"sess-1"}])", "application/json");
        });
        svr_.Post("/session/sess-1/prompt_async", [this](const httplib::Request &, httplib::Response &res) {
            std::lock_guard<std::mutex> lock(mtx_);
            res.status = promptStatus_;
            res.set_content("", "application/json");
        });
        svr_.Get("/session/sess-1/message", [this](const httplib::Request &, httplib::Response &res) {
            std::lock_guard<std::mutex> lock(mtx_);
            res.status = messageStatus_;
            res.set_content(messageBody_, "application/json");
        });
    }

    ~FakeOpencodeServer() { Stop(); }

    int Start()
    {
        const int port = svr_.bind_to_any_port("127.0.0.1");
        if (port <= 0) {
            return -1;
        }
        thread_ = std::thread([this] { svr_.listen_after_bind(); });
        for (int i = 0; i < SERVER_START_ROUNDS && !svr_.is_running(); ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(SERVER_POLL_INTERVAL_MS));
        }
        return svr_.is_running() ? port : -1;
    }

    void Stop()
    {
        svr_.stop();
        if (thread_.joinable()) {
            thread_.join();
        }
    }

    void SetSessionPostResponse(int status, const std::string &body)
    {
        std::lock_guard<std::mutex> lock(mtx_);
        sessionPostStatus_ = status;
        sessionPostBody_ = body;
    }

    void SetSessionGetStatus(int status)
    {
        std::lock_guard<std::mutex> lock(mtx_);
        sessionGetStatus_ = status;
    }

    void SetPromptStatus(int status)
    {
        std::lock_guard<std::mutex> lock(mtx_);
        promptStatus_ = status;
    }

    void SetMessageResponse(int status, const std::string &body)
    {
        std::lock_guard<std::mutex> lock(mtx_);
        messageStatus_ = status;
        messageBody_ = body;
    }

private:
    httplib::Server svr_;
    std::thread thread_;
    std::mutex mtx_;
    int sessionPostStatus_ = HTTP_OK;
    std::string sessionPostBody_ = R"({"id":"sess-1"})";
    int sessionGetStatus_ = HTTP_OK;
    int promptStatus_ = HTTP_NO_CONTENT;
    int messageStatus_ = HTTP_OK;
    std::string messageBody_;
};

// 一条已完成的 assistant 消息（多 parts，含非 text 类型）+ 一条 user 消息
std::string MakeCompletedMessages()
{
    Json::Value arr(Json::arrayValue);
    Json::Value user = MakeMessage("user", MSG_TS_1);
    Json::Value assistant = MakeMessage("assistant", MSG_TS_3);
    assistant["info"]["time"]["completed"] = MSG_TS_5;
    Json::Value p1(Json::objectValue);
    p1["type"] = "text";
    p1["text"] = "answer part 1";
    Json::Value p2(Json::objectValue);
    p2["type"] = "image";
    p2["url"] = "http://x";
    Json::Value p3(Json::objectValue);
    p3["type"] = "text";
    p3["text"] = "answer part 2";
    assistant["parts"].append(p1);
    assistant["parts"].append(p2);
    assistant["parts"].append(p3);
    arr.append(user);
    arr.append(assistant);
    return Json::writeString(Json::StreamWriterBuilder(), arr);
}

} // namespace

class OpencodeServerTest : public ::testing::Test {
protected:
    void SetUp() override
    {
        server_ = std::make_unique<FakeOpencodeServer>();
        port_ = server_->Start();
        ASSERT_GT(port_, 0);
        server_->SetMessageResponse(HTTP_OK, MakeCompletedMessages());
    }

    void TearDown() override
    {
        server_->Stop();
        server_.reset();
    }

    // 连接信息直连本地模拟服务（私有成员经 #define private public 可见）
    void PointToServer(code_analyzer::CodeAnalyzer &analyzer) const
    {
        analyzer.conn_.url = "http://127.0.0.1";
        analyzer.conn_.port = port_;
        analyzer.sessionId_ = "sess-1";
    }

    std::unique_ptr<FakeOpencodeServer> server_;
    int port_ = 0;
};

// ---------------------------------------------------------------------------
// CreateSession
// ---------------------------------------------------------------------------
TEST_F(OpencodeServerTest, CreateSessionSucceeds)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    EXPECT_EQ(analyzer.CreateSession(), RACK_OK);
    EXPECT_EQ(analyzer.sessionId_, "sess-1");
}

TEST_F(OpencodeServerTest, CreateSessionFailsOnServerError)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetSessionPostResponse(HTTP_SERVER_ERROR, R"({"id":"x"})");
    EXPECT_EQ(analyzer.CreateSession(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, CreateSessionFailsOnBadJson)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetSessionPostResponse(HTTP_OK, "not-a-json");
    EXPECT_EQ(analyzer.CreateSession(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, CreateSessionFailsWithoutServer)
{
    code_analyzer::CodeAnalyzer analyzer;
    analyzer.conn_.url = "http://127.0.0.1";
    analyzer.conn_.port = 1; // 回环拒绝端口：连接立即失败
    EXPECT_EQ(analyzer.CreateSession(), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// WaitForSessionVisible
// ---------------------------------------------------------------------------
TEST_F(OpencodeServerTest, WaitForSessionVisibleSucceeds)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    EXPECT_EQ(analyzer.WaitForSessionVisible(), RACK_OK);
}

TEST_F(OpencodeServerTest, WaitForSessionVisibleTimesOutOnServerError)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetSessionGetStatus(HTTP_SERVER_ERROR);
    // 非就绪状态轮询约 5 秒后超时
    EXPECT_EQ(analyzer.WaitForSessionVisible(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, WaitForSessionVisibleTimesOutWithoutServer)
{
    code_analyzer::CodeAnalyzer analyzer;
    analyzer.conn_.url = "http://127.0.0.1";
    analyzer.conn_.port = 1;
    analyzer.sessionId_ = "sess-1";
    // 连接失败同样轮询直至超时
    EXPECT_EQ(analyzer.WaitForSessionVisible(), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// SendMessageAsync
// ---------------------------------------------------------------------------
TEST_F(OpencodeServerTest, SendMessageAsyncSucceeds)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    EXPECT_EQ(analyzer.SendMessageAsync("analyze this"), RACK_OK);
    EXPECT_GT(analyzer.promptSubmittedAtMs_, 0);
}

TEST_F(OpencodeServerTest, SendMessageAsyncFailsOnBadStatus)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetPromptStatus(HTTP_SERVER_ERROR);
    EXPECT_EQ(analyzer.SendMessageAsync("analyze this"), RACK_FAIL);
}

TEST_F(OpencodeServerTest, SendMessageAsyncFailsWithoutServer)
{
    code_analyzer::CodeAnalyzer analyzer;
    analyzer.conn_.url = "http://127.0.0.1";
    analyzer.conn_.port = 1;
    analyzer.sessionId_ = "sess-1";
    EXPECT_EQ(analyzer.SendMessageAsync("analyze this"), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// WaitForAssistantMessageCompleted（成功路径立即返回；失败路径均不进入长轮询）
// ---------------------------------------------------------------------------
TEST_F(OpencodeServerTest, WaitForAssistantMessageCompletedSucceeds)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    EXPECT_EQ(analyzer.WaitForAssistantMessageCompleted(), RACK_OK);
}

TEST_F(OpencodeServerTest, WaitForAssistantMessageCompletedFailsOnBadStatus)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_NOT_FOUND, "{}");
    EXPECT_EQ(analyzer.WaitForAssistantMessageCompleted(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, WaitForAssistantMessageCompletedFailsOnBadJson)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_OK, "not-a-json");
    EXPECT_EQ(analyzer.WaitForAssistantMessageCompleted(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, WaitForAssistantMessageCompletedFailsOnNonArray)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_OK, R"({"a":1})");
    EXPECT_EQ(analyzer.WaitForAssistantMessageCompleted(), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// FetchLatestAssistantMessage
// ---------------------------------------------------------------------------
TEST_F(OpencodeServerTest, FetchLatestAssistantMessageSucceeds)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    EXPECT_EQ(analyzer.FetchLatestAssistantMessage(), RACK_OK);
}

TEST_F(OpencodeServerTest, FetchLatestAssistantMessageEmptyTextStillOk)
{
    // assistant 消息无 text part：text 为空，仅打日志，仍返回成功
    Json::Value arr(Json::arrayValue);
    Json::Value assistant = MakeMessage("assistant", MSG_TS_3);
    assistant["info"]["time"]["completed"] = MSG_TS_5;
    Json::Value part(Json::objectValue);
    part["type"] = "image";
    part["url"] = "http://x";
    assistant["parts"].append(part);
    arr.append(assistant);
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_OK, Json::writeString(Json::StreamWriterBuilder(), arr));
    EXPECT_EQ(analyzer.FetchLatestAssistantMessage(), RACK_OK);
}

TEST_F(OpencodeServerTest, FetchLatestAssistantMessageFailsWhenNoAssistant)
{
    Json::Value arr(Json::arrayValue);
    arr.append(MakeMessage("user", MSG_TS_1));
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_OK, Json::writeString(Json::StreamWriterBuilder(), arr));
    EXPECT_EQ(analyzer.FetchLatestAssistantMessage(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, FetchLatestAssistantMessageFailsOnBadStatus)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_SERVER_ERROR, "[]");
    EXPECT_EQ(analyzer.FetchLatestAssistantMessage(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, FetchLatestAssistantMessageFailsOnBadJson)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_OK, "not-a-json");
    EXPECT_EQ(analyzer.FetchLatestAssistantMessage(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, FetchLatestAssistantMessageFailsOnNonArray)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetMessageResponse(HTTP_OK, R"({"a":1})");
    EXPECT_EQ(analyzer.FetchLatestAssistantMessage(), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// Run / Start 全链路
// ---------------------------------------------------------------------------
TEST_F(OpencodeServerTest, RunSucceedsEndToEnd)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    EXPECT_EQ(analyzer.Run("my-skill", "do analysis"), RACK_OK);
    EXPECT_EQ(analyzer.sessionId_, "sess-1");
}

TEST_F(OpencodeServerTest, RunFailsWhenPromptRejected)
{
    code_analyzer::CodeAnalyzer analyzer;
    PointToServer(analyzer);
    server_->SetPromptStatus(HTTP_SERVER_ERROR);
    EXPECT_EQ(analyzer.Run("my-skill", "do analysis"), RACK_FAIL);
}

TEST_F(OpencodeServerTest, CodeAnalyzerStartSucceedsEndToEnd)
{
    // 4 个组件 analyzer + 1 次 aggregation + 1 次 keyfunc 全部成功
    SetArgMap(FullArgs(std::to_string(port_)));
    code_analyzer::CodeAnalyzer analyzer;
    ASSERT_EQ(analyzer.Initialize(), RACK_OK);
    EXPECT_EQ(analyzer.Start(), RACK_OK);
    analyzer.Stop();
    analyzer.UnInitialize();
}

TEST_F(OpencodeServerTest, CodeAnalyzerStartFailsWhenSkillRunFails)
{
    SetArgMap(FullArgs(std::to_string(port_)));
    code_analyzer::CodeAnalyzer analyzer;
    ASSERT_EQ(analyzer.Initialize(), RACK_OK);
    server_->SetPromptStatus(HTTP_SERVER_ERROR);
    EXPECT_EQ(analyzer.Start(), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// CodeAnalyzerModule 生命周期
// ---------------------------------------------------------------------------
TEST_F(OpencodeServerTest, ModuleLifecycleSucceeds)
{
    SetArgMap(FullArgs(std::to_string(port_)));
    code_analyzer::CodeAnalyzerModule module;
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_NE(module.GetCodeAnalyzer(), nullptr);
    EXPECT_EQ(module.Start(), RACK_OK);
    module.Stop();
    module.UnInitialize();
}

TEST(CodeAnalyzerModuleLifecycle, InitializeFailsWithoutArguments)
{
    SetArgMap({});
    code_analyzer::CodeAnalyzerModule module;
    EXPECT_EQ(module.Initialize(), RACK_FAIL);
}

TEST_F(OpencodeServerTest, ModuleStartFailsWhenServerUnreachable)
{
    SetArgMap(FullArgs("1")); // 回环拒绝端口
    code_analyzer::CodeAnalyzerModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    EXPECT_EQ(module.Start(), RACK_FAIL);
    module.Stop();
    module.UnInitialize();
}
