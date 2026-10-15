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

// B3 B 级：rack_http 库——路由注册/分发、HTTP 方法转换、请求校验与响应回填。
// 不监听端口、不启动服务线程：全部经 RackHttpServerHandler 单例与 RackHttpServer 的
// 公共纯函数（ValidateHttpRequest / GenerateQueryString / HandlerRequest）覆盖。

#include <gtest/gtest.h>

#include <atomic>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <httplib.h>

#include "http/rack_http_server.h"
#include "http/rack_http_server_handler.h"
#include "logger.h"

// ---------------------------------------------------------------------------
// log4cplus 链接桩：rack_http 未传递 log4cplus，而其 LOG_* 宏引用以下符号。
// 不调用 rack::logger::init，g_logger 保持默认构造、isEnabledFor 恒 false，日志被丢弃。
// ---------------------------------------------------------------------------
namespace log4cplus {
namespace helpers {
void SharedObject::addReference() const LOG4CPLUS_NOEXCEPT {}
void SharedObject::removeReference() const {}
} // namespace helpers
namespace spi {
AppenderAttachable::~AppenderAttachable() {}
} // namespace spi
Logger::Logger() LOG4CPLUS_NOEXCEPT {}
Logger::~Logger() {}
bool Logger::isEnabledFor(LogLevel) const
{
    return false;
}
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
// 固定端口/超时：RackHttpServer::Initialize 为 call_once，端口由首次调用决定
constexpr int K_RACK_HTTP_SERVER_PORT = 28081;
constexpr int K_TEST_ALT_PORT = 28082;   // Initialize 幂等用例的第二个端口参数（仅首次生效）
constexpr int K_TEST_REMOTE_PORT = 39000; // 请求来源端口（仅回填，无实际连接语义）
constexpr int K_CLIENT_TIMEOUT_SEC = 2;   // httplib 客户端连接超时（秒）

// 构造一个返回固定响应的 handler
rack::com::RackHttpHandler MakeHandler(int status, std::string body)
{
    return [status, body](const rack::com::RackComContext &,
                          const rack::com::RackHttpRequest &) -> rack::com::RackComResult<rack::com::RackHttpResponse> {
        rack::com::RackHttpResponse resp;
        resp.status = status;
        resp.body = body;
        return rack::com::RackComResult<rack::com::RackHttpResponse>::Ok(std::move(resp));
    };
}

rack::com::RackHttpRequest MakeRequest(rack::com::RackHttpMethod method, std::string path)
{
    rack::com::RackHttpRequest req;
    req.method = method;
    req.path = std::move(path);
    return req;
}

bool HasRoute(const std::string &key)
{
    const auto &routes = rack::com::RackHttpServerHandler::GetInstance().routes();
    return routes.find(key) != routes.end();
}
} // namespace

// ---------------------------------------------------------------------------
// MethodToString / StringToMethod：全枚举往返
// ---------------------------------------------------------------------------
TEST(HttpMethodConvert, RoundTripAllMethods)
{
    using rack::com::RackHttpMethod;
    EXPECT_EQ(rack::com::MethodToString(RackHttpMethod::GET), "GET");
    EXPECT_EQ(rack::com::MethodToString(RackHttpMethod::POST), "POST");
    EXPECT_EQ(rack::com::MethodToString(RackHttpMethod::PUT), "PUT");
    EXPECT_EQ(rack::com::MethodToString(RackHttpMethod::DELETE_), "DELETE");
    EXPECT_EQ(rack::com::MethodToString(RackHttpMethod::PATCH), "PATCH");
    EXPECT_EQ(rack::com::MethodToString(RackHttpMethod::OPTIONS), "OPTIONS");
    // 无效枚举值：走 default 返回 "INVALID"
    EXPECT_EQ(rack::com::MethodToString(RackHttpMethod::INVALID), "INVALID");

    EXPECT_EQ(rack::com::StringToMethod("GET"), RackHttpMethod::GET);
    EXPECT_EQ(rack::com::StringToMethod("POST"), RackHttpMethod::POST);
    EXPECT_EQ(rack::com::StringToMethod("PUT"), RackHttpMethod::PUT);
    EXPECT_EQ(rack::com::StringToMethod("DELETE"), RackHttpMethod::DELETE_);
    EXPECT_EQ(rack::com::StringToMethod("PATCH"), RackHttpMethod::PATCH);
    EXPECT_EQ(rack::com::StringToMethod("OPTIONS"), RackHttpMethod::OPTIONS);
    EXPECT_EQ(rack::com::StringToMethod("FOO"), RackHttpMethod::INVALID);
    EXPECT_EQ(rack::com::StringToMethod("get"), RackHttpMethod::INVALID); // 大小写敏感
}

// ---------------------------------------------------------------------------
// Register / MakeKey 归一化 / Dispatch 精确匹配
// ---------------------------------------------------------------------------
TEST(RouteDispatch, RegisterAndExactMatch)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/exact", MakeHandler(200, "ok-exact"));

    rack::com::RackComContext ctx;
    auto result = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/exact"));
    EXPECT_TRUE(result.Ok());
    ASSERT_TRUE(result.value.has_value());
    EXPECT_EQ(result.value->status, 200);
    EXPECT_EQ(result.value->body, "ok-exact");
    // 路由表以 "GET /b3/exact" 为键存在
    EXPECT_TRUE(HasRoute("GET /b3/exact"));
}

// MakeKey 归一化：空 path 补 "/"；缺前导斜杠补 "/"
TEST(RouteDispatch, RegisterNormalizesPath)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "b3/noslash", MakeHandler(201, "noslash"));
    EXPECT_TRUE(HasRoute("GET /b3/noslash"));

    handler.Register(rack::com::RackHttpMethod::GET, "", MakeHandler(202, "root"));
    EXPECT_TRUE(HasRoute("GET /"));

    rack::com::RackComContext ctx;
    auto r1 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/noslash"));
    ASSERT_TRUE(r1.Ok());
    EXPECT_EQ(r1.value->status, 201);

    auto r2 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/"));
    ASSERT_TRUE(r2.Ok());
    EXPECT_EQ(r2.value->status, 202);
}

// 同 method 不同 path、同 path 不同 method 互不干扰
TEST(RouteDispatch, MethodAndPathArePartOfKey)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/mix", MakeHandler(200, "get-only"));

    rack::com::RackComContext ctx;
    // POST 请求未注册 -> route not found
    auto r = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::POST, "/b3/mix"));
    EXPECT_FALSE(r.Ok());
    EXPECT_EQ(r.code, rack::com::RackComError::UNAVAILABLE);
    EXPECT_EQ(r.message, "route not found");

    // 未注册路径
    auto r2 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/other"));
    EXPECT_FALSE(r2.Ok());
    EXPECT_EQ(r2.code, rack::com::RackComError::UNAVAILABLE);

    // GET 命中
    auto r3 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/mix"));
    ASSERT_TRUE(r3.Ok());
    EXPECT_EQ(r3.value->body, "get-only");
}

// 重复注册：同键二次 Register 被忽略，保留首个 handler
TEST(RouteDispatch, DuplicateRegisterKeepsFirstHandler)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/dup", MakeHandler(200, "first"));
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/dup", MakeHandler(200, "second"));

    rack::com::RackComContext ctx;
    auto r = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/dup"));
    ASSERT_TRUE(r.Ok());
    EXPECT_EQ(r.value->body, "first");
}

// 通配符路由："/prefix/*" 匹配以 prefix 开头的请求（前缀匹配，不校验段边界）
TEST(RouteDispatch, WildcardPrefixMatch)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/w/*", MakeHandler(200, "wild"));

    rack::com::RackComContext ctx;
    // 深层路径命中
    auto r1 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/w/a/b/c"));
    ASSERT_TRUE(r1.Ok());
    EXPECT_EQ(r1.value->body, "wild");

    // 前缀本身命中（prefix="/b3/w"，"/b3/w" 以其开头）
    auto r2 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/w"));
    ASSERT_TRUE(r2.Ok());

    // 无关前缀不命中（"/b3/x" 不以 "/b3/w" 开头）
    auto r3 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/x"));
    EXPECT_FALSE(r3.Ok());
    EXPECT_EQ(r3.code, rack::com::RackComError::UNAVAILABLE);

    // 通配仅作用于注册的 method：POST 不命中 GET 通配
    auto r4 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::POST, "/b3/w/x"));
    EXPECT_FALSE(r4.Ok());
}

// 多个通配命中时取最长前缀
TEST(RouteDispatch, WildcardChoosesLongestPrefix)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/lp/*", MakeHandler(200, "short"));
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/lp/deep/*", MakeHandler(200, "long"));

    rack::com::RackComContext ctx;
    // 深路径命中更长前缀
    auto r1 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/lp/deep/x"));
    ASSERT_TRUE(r1.Ok());
    EXPECT_EQ(r1.value->body, "long");

    // 浅路径只命中短前缀
    auto r2 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/lp/other"));
    ASSERT_TRUE(r2.Ok());
    EXPECT_EQ(r2.value->body, "short");
}

// 精确匹配优先于通配
TEST(RouteDispatch, ExactMatchBeatsWildcard)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/pw/*", MakeHandler(200, "wild"));
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/pw", MakeHandler(200, "exact"));

    rack::com::RackComContext ctx;
    auto r = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/pw"));
    ASSERT_TRUE(r.Ok());
    EXPECT_EQ(r.value->body, "exact");
}

// context.cancelled 为 true：直接返回 CANCELLED，不调用任何 handler
TEST(RouteDispatch, CancelledContextShortCircuits)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/cancel", MakeHandler(200, "never"));

    std::atomic<bool> cancelled{true};
    rack::com::RackComContext ctx;
    ctx.cancelled = &cancelled;
    auto r = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/cancel"));
    EXPECT_FALSE(r.Ok());
    EXPECT_EQ(r.code, rack::com::RackComError::CANCELLED);
    EXPECT_EQ(r.message, "cancelled");

    // cancelled 为 false：正常分发
    cancelled.store(false);
    auto r2 = handler.Dispatch(ctx, MakeRequest(rack::com::RackHttpMethod::GET, "/b3/cancel"));
    ASSERT_TRUE(r2.Ok());
    EXPECT_EQ(r2.value->body, "never");
}

// Use 仅追加中间件（当前 Dispatch 不应用中间件，验证存储行为）
TEST(RouteDispatch, UseAppendsMiddleware)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    const size_t before = handler.middlewares().size();
    handler.Use([](rack::com::RackHttpHandler h) { return h; });
    EXPECT_EQ(handler.middlewares().size(), before + 1);
}

// 并发注册不同路径互不干扰（mutex 生效）
TEST(RouteDispatch, ConcurrentRegisterIsSafe)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    std::vector<std::thread> threads;
    for (int i = 0; i < 8; ++i) {
        threads.emplace_back([&handler, i]() {
            handler.Register(rack::com::RackHttpMethod::GET, "/b3/conc/" + std::to_string(i),
                             MakeHandler(200, "c" + std::to_string(i)));
        });
    }
    for (auto &t : threads) {
        t.join();
    }
    for (int i = 0; i < 8; ++i) {
        EXPECT_TRUE(HasRoute("GET /b3/conc/" + std::to_string(i)));
    }
}

// ---------------------------------------------------------------------------
// RackHttpServer：请求校验与查询串构造（不起服务）
// ---------------------------------------------------------------------------
class RackHttp : public ::testing::Test {
public:
    RackHttp()
    {
        // ctest 隔离模式下每个用例单独进程，不能依赖 InitializeCreatesSingletonInstance
        // 先跑；call_once 幂等，已初始化时无副作用（端口与 B5 回环用例一致）。
        rack::com::RackHttpServer::Initialize(K_RACK_HTTP_SERVER_PORT);
    }

protected:
    rack::com::RackHttpServer &server() { return rack::com::RackHttpServer::GetInstance(); }
};

// Initialize 后 GetInstance 可用；Start 未调用时不监听端口
TEST_F(RackHttp, InitializeCreatesSingletonInstance)
{
    // call_once 幂等；不同端口参数仅在首次生效
    EXPECT_TRUE(rack::com::RackHttpServer::Initialize(K_RACK_HTTP_SERVER_PORT));
    EXPECT_TRUE(rack::com::RackHttpServer::Initialize(K_TEST_ALT_PORT));
    EXPECT_NO_THROW(rack::com::RackHttpServer::GetInstance());
}

// GenerateQueryString：空/单项/多项拼接
TEST_F(RackHttp, GenerateQueryString)
{
    EXPECT_EQ(server().GenerateQueryString({}), "");

    httplib::Params single{{"a", "1"}};
    EXPECT_EQ(server().GenerateQueryString(single), "a=1");

    httplib::Params multi{{"a", "1"}, {"b", "2"}};
    EXPECT_EQ(server().GenerateQueryString(multi), "a=1&b=2");
}

// ValidateHttpRequest：合法方法、非法方法、body 超限、query 超限
TEST_F(RackHttp, ValidateHttpRequestBranches)
{
    rack::com::RackHttpRequest out;

    // 合法方法解析成功
    httplib::Request okReq;
    okReq.method = "GET";
    EXPECT_EQ(server().ValidateHttpRequest(okReq, out), RACK_OK);
    EXPECT_EQ(out.method, rack::com::RackHttpMethod::GET);

    // 非法方法 -> RACK_FAIL 且 method 为 INVALID
    httplib::Request badReq;
    badReq.method = "TRACE";
    EXPECT_EQ(server().ValidateHttpRequest(badReq, out), RACK_FAIL);
    EXPECT_EQ(out.method, rack::com::RackHttpMethod::INVALID);

    // body 超过 512 KiB 上限 -> RACK_FAIL
    httplib::Request bigBody;
    bigBody.method = "POST";
    bigBody.body.assign(rack::com::httpMaxBodySize + 1, 'x');
    EXPECT_EQ(server().ValidateHttpRequest(bigBody, out), RACK_FAIL);

    // query 串超过 11264 上限 -> RACK_FAIL
    httplib::Request bigQuery;
    bigQuery.method = "GET";
    bigQuery.params.emplace("q", std::string(rack::com::httpMaxQuerySize + 1, 'x'));
    EXPECT_EQ(server().ValidateHttpRequest(bigQuery, out), RACK_FAIL);
}

// HandlerRequest：非法方法 -> 400
TEST_F(RackHttp, HandlerRequestRejectsInvalidMethod)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::POST, "/b3/hr", MakeHandler(rack::com::OK_200, "hr"));

    httplib::Request req;
    req.method = "TRACE";
    req.path = "/b3/hr";
    httplib::Response res;
    server().HandlerRequest(req, res);
    EXPECT_EQ(res.status, rack::com::BadRequest_400);
    EXPECT_EQ(res.body, "The request is invalid.");
}

// HandlerRequest：未注册路由 -> 500 route not found
TEST_F(RackHttp, HandlerRequestUnknownRouteReturns500)
{
    httplib::Request req;
    req.method = "GET";
    req.path = "/b3/no_such_route";
    httplib::Response res;
    server().HandlerRequest(req, res);
    EXPECT_EQ(res.status, rack::com::InternalServerError_500);
    EXPECT_EQ(res.body, "route not found");
}

// HandlerRequest：正常分发回填状态码、body 与 Content-Type 头
TEST_F(RackHttp, HandlerRequestFillsResponse)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/full",
        [](const rack::com::RackComContext &, const rack::com::RackHttpRequest &request) {
            rack::com::RackHttpResponse resp;
            resp.status = rack::com::Created_201;
            resp.body = "{\"k\":\"" + request.queryParams.at("q") + "\"}";
            resp.headers["Content-Type"] = "application/json";
            return rack::com::RackComResult<rack::com::RackHttpResponse>::Ok(std::move(resp));
        });

    httplib::Request req;
    req.method = "GET";
    req.path = "/b3/full";
    req.params.emplace("q", "v1");
    req.headers.emplace("X-Custom", "h1");
    req.body = "payload";
    req.remote_addr = "127.0.0.1";
    req.remote_port = K_TEST_REMOTE_PORT;

    httplib::Response res;
    server().HandlerRequest(req, res);
    EXPECT_EQ(res.status, rack::com::Created_201);
    EXPECT_EQ(res.body, "{\"k\":\"v1\"}");
    EXPECT_TRUE(res.has_header("Content-Type"));
    EXPECT_EQ(res.get_header_value("Content-Type"), "application/json");
}

// HandlerRequest：handler 返回 Error -> 500 且 body 为错误消息
TEST_F(RackHttp, HandlerRequestPropagatesHandlerError)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b3/err",
        [](const rack::com::RackComContext &, const rack::com::RackHttpRequest &) {
            return rack::com::RackComResult<rack::com::RackHttpResponse>::Error(rack::com::RackComError::INTERNAL,
                "boom");
        });

    httplib::Request req;
    req.method = "GET";
    req.path = "/b3/err";
    httplib::Response res;
    server().HandlerRequest(req, res);
    EXPECT_EQ(res.status, rack::com::InternalServerError_500);
    EXPECT_EQ(res.body, "boom");
}

// ---------------------------------------------------------------------------
// B5 追加：真实 Start/Stop（本机回环）。既有测试已 Initialize(K_RACK_HTTP_SERVER_PORT)（call_once，
// 端口固定），以下仅在回环地址上启动/停止，并经 httplib::Client 走真实 HTTP
// 请求全链路（Run → ConfigureRoutes → EnsurePortAvailable → HandlerRequest）。
// 注：不测“端口被占 → Start 超时返回 false”路径——Run 线程异常退出后 thread_
// 永不 join，进程退出时析构未 join 的 std::thread 会 std::terminate 崩掉二进制。
// ---------------------------------------------------------------------------
namespace {
// 占用型 POST handler：回显请求 body，验证真实连接下 body 透传
rack::com::RackComResult<rack::com::RackHttpResponse> EchoPostHandler(
    const rack::com::RackComContext &, const rack::com::RackHttpRequest &req)
{
    rack::com::RackHttpResponse resp;
    resp.status = rack::com::Created_201;
    resp.body = "echo:" + req.body;
    resp.headers["X-B5"] = "hdr";
    return rack::com::RackComResult<rack::com::RackHttpResponse>::Ok(std::move(resp));
}
} // namespace

// Start 成功（回环监听建立）；运行中再次 Start 走 is_running 短路直接返回 true
TEST_F(RackHttp, StartIsIdempotentWhileRunning)
{
    ASSERT_TRUE(server().Start());
    // 已运行：is_running() 为真分支，不新建线程
    EXPECT_TRUE(server().Start());
    server().Stop();
}

// 未运行时 Stop：!is_running() 早退分支，无副作用
TEST_F(RackHttp, StopWhenNotRunningIsNoop)
{
    EXPECT_NO_THROW(server().Stop());
}

// 停止后可再次 Start：thread_ 已 join，可安全重建监听（重复 ConfigureRoutes 无害）。
// 注：本用例刻意不发任何客户端请求——服务端先关闭 keep-alive 连接会在服务端口上
// 留下 TIME-WAIT，使后续 Start() 的 EnsurePortAvailable bind 失败（已实测）。
// 因此本用例必须放在 RealLoopbackRequestEndToEnd 之前执行。
TEST_F(RackHttp, RestartAfterStopSucceeds)
{
    ASSERT_TRUE(server().Start());
    server().Stop();

    ASSERT_TRUE(server().Start());
    server().Stop();
}

// 真实回环请求全链路：GET 带 query、POST 带 body/自定义头、未注册路由 500
TEST_F(RackHttp, RealLoopbackRequestEndToEnd)
{
    auto &handler = rack::com::RackHttpServerHandler::GetInstance();
    handler.Register(rack::com::RackHttpMethod::GET, "/b5/live", MakeHandler(rack::com::OK_200, "live-ok"));
    handler.Register(rack::com::RackHttpMethod::POST, "/b5/live", EchoPostHandler);

    ASSERT_TRUE(server().Start());

    httplib::Client cli("127.0.0.1", K_RACK_HTTP_SERVER_PORT);
    cli.set_connection_timeout(K_CLIENT_TIMEOUT_SEC);

    // GET + query 经真实 socket：HandlerRequest 解析 params 并精确分发
    auto res = cli.Get("/b5/live?q=1");
    ASSERT_TRUE(res != nullptr);
    EXPECT_EQ(res->status, rack::com::OK_200);
    EXPECT_EQ(res->body, "live-ok");

    // POST + body + 响应头回填
    auto res2 = cli.Post("/b5/live", "payload", "text/plain");
    ASSERT_TRUE(res2 != nullptr);
    EXPECT_EQ(res2->status, rack::com::Created_201);
    EXPECT_EQ(res2->body, "echo:payload");
    EXPECT_EQ(res2->get_header_value("X-B5"), "hdr");

    // 未注册路由经真实连接 -> 500 route not found
    auto res3 = cli.Get("/b5/no_such");
    ASSERT_TRUE(res3 != nullptr);
    EXPECT_EQ(res3->status, rack::com::InternalServerError_500);
    EXPECT_EQ(res3->body, "route not found");

    server().Stop();
    // 停止后连接被拒
    auto res4 = cli.Get("/b5/live");
    EXPECT_TRUE(res4 == nullptr);
}
