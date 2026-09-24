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

// B4 C 级浅测：rack::com::RackHttpClient
// 只测 URL/配置存储、请求构造与错误路径，不依赖任何真实网络服务：
//  - 不支持的方法分支为纯逻辑，零网络 IO；
//  - 连接类用例统一指向回环地址保留端口 1（本机无监听，连接立即被拒绝，
//    既不起服务也不监听端口，属于确定性的错误路径）。

#include <gtest/gtest.h>

// 标准库头先于 private→public 宏包含，避免宏污染
#include <atomic>
#include <chrono>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "common/rack_com_context.h"
#include "http/rack_http_types.h"
#include "http/rack_http_client_handler.h"

// 打开私有成员用于断言 baseUrl_ 的存储（本仓库既有测试模式）
#define private public
#include "http/rack_http_client.h"
#undef private

#include "logger.h"

namespace {

// 打日志的库必须先初始化 log4cplus，否则 SEGFAULT。
struct LoggerInit {
    LoggerInit() { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 回环 + 保留端口 1：本机必然无监听，连接立即失败
const std::string REFUSED_BASE_URL = "http://127.0.0.1:1";

// 构造一个带基础字段的请求
rack::com::RackHttpRequest MakeRequest(rack::com::RackHttpMethod method)
{
    rack::com::RackHttpRequest req;
    req.method = method;
    req.path = "/test/path";
    req.body = "hello-body";
    req.headers["X-Test"] = "1";
    return req;
}

// 断言 Do() 走连接失败错误路径（不关心具体失败原因：拒绝/被拦截/超时均为 UNAVAILABLE）
void ExpectConnectionFailure(const rack::com::RackComResult<rack::com::RackHttpResponse> &res)
{
    EXPECT_FALSE(res.Ok());
    EXPECT_EQ(res.code, rack::com::RackComError::UNAVAILABLE);
    EXPECT_NE(res.message.find("http request failed"), std::string::npos);
    EXPECT_FALSE(res.value.has_value());
}

} // namespace

// ---------------------------------------------------------------------------
// 构造与配置
// ---------------------------------------------------------------------------

// baseUrl 原样存储
TEST(RackHttpClient, ConstructStoresHttpBaseUrl)
{
    rack::com::RackHttpClient client("http://127.0.0.1:8080");
    EXPECT_EQ(client.baseUrl_, "http://127.0.0.1:8080");
}

// https 前缀同样原样存储（Do 时才启用证书校验配置）
TEST(RackHttpClient, ConstructStoresHttpsBaseUrl)
{
    rack::com::RackHttpClient client("https://127.0.0.1:8443");
    EXPECT_EQ(client.baseUrl_, "https://127.0.0.1:8443");
}

// 空 baseUrl 也可构造，仅存储不解析
TEST(RackHttpClient, ConstructAcceptsEmptyBaseUrl)
{
    rack::com::RackHttpClient client("");
    EXPECT_EQ(client.baseUrl_, "");
}

// ---------------------------------------------------------------------------
// 不支持的方法：纯逻辑错误路径，零网络 IO
// ---------------------------------------------------------------------------

// PATCH 未实现，Do 必须直接返回"方法不支持"，且不发起任何连接
TEST(RackHttpClient, DoPatchMethodNotSupported)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackComContext ctx;
    auto res = client.Do(ctx, MakeRequest(rack::com::RackHttpMethod::PATCH));
    EXPECT_FALSE(res.Ok());
    EXPECT_EQ(res.code, rack::com::RackComError::UNAVAILABLE);
    EXPECT_EQ(res.message, "http method not supported");
    EXPECT_FALSE(res.value.has_value());
}

// INVALID 方法同样被拒绝
TEST(RackHttpClient, DoInvalidMethodNotSupported)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackComContext ctx;
    auto res = client.Do(ctx, MakeRequest(rack::com::RackHttpMethod::INVALID));
    EXPECT_FALSE(res.Ok());
    EXPECT_EQ(res.code, rack::com::RackComError::UNAVAILABLE);
    EXPECT_EQ(res.message, "http method not supported");
    EXPECT_FALSE(res.value.has_value());
}

// 通过基类引用调用，验证虚函数多态分发
TEST(RackHttpClient, DoDispatchesThroughBaseHandler)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackHttpClientHandler &handler = client;
    rack::com::RackComContext ctx;
    auto res = handler.Do(ctx, MakeRequest(rack::com::RackHttpMethod::PATCH));
    EXPECT_FALSE(res.Ok());
    EXPECT_EQ(res.message, "http method not supported");
}

// ---------------------------------------------------------------------------
// 连接失败错误路径（回环保留端口，立即拒绝，不起任何服务）
// ---------------------------------------------------------------------------

// GET：连接失败映射为 UNAVAILABLE，message 带统一前缀
TEST(RackHttpClient, DoGetConnectionFailed)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackComContext ctx;
    ExpectConnectionFailure(client.Do(ctx, MakeRequest(rack::com::RackHttpMethod::GET)));
}

// POST：带 Content-Type 的请求体分支（SendWithBody 提取并移除 Content-Type）
TEST(RackHttpClient, DoPostWithContentTypeConnectionFailed)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackComContext ctx;
    auto req = MakeRequest(rack::com::RackHttpMethod::POST);
    req.headers["Content-Type"] = "application/json";
    req.body = R"({"k":"v"})";
    ExpectConnectionFailure(client.Do(ctx, req));
}

// PUT：无 Content-Type 时走默认 text/plain 分支
TEST(RackHttpClient, DoPutDefaultContentTypeConnectionFailed)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackComContext ctx;
    auto req = MakeRequest(rack::com::RackHttpMethod::PUT);
    req.body = "plain-text";
    ExpectConnectionFailure(client.Do(ctx, req));
}

// DELETE：无请求体分支
TEST(RackHttpClient, DoDeleteConnectionFailed)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackComContext ctx;
    auto req = MakeRequest(rack::com::RackHttpMethod::DELETE_);
    req.body.clear();
    ExpectConnectionFailure(client.Do(ctx, req));
}

// OPTIONS：无 headers 分支
TEST(RackHttpClient, DoOptionsConnectionFailed)
{
    rack::com::RackHttpClient client(REFUSED_BASE_URL);
    rack::com::RackComContext ctx;
    auto req = MakeRequest(rack::com::RackHttpMethod::OPTIONS);
    req.headers.clear();
    ExpectConnectionFailure(client.Do(ctx, req));
}

// https 前缀触发证书校验配置路径，连接失败同样映射为 UNAVAILABLE
TEST(RackHttpClient, DoHttpsBaseUrlConnectionFailed)
{
    rack::com::RackHttpClient client("https://127.0.0.1:1");
    rack::com::RackComContext ctx;
    ExpectConnectionFailure(client.Do(ctx, MakeRequest(rack::com::RackHttpMethod::GET)));
}

// 请求结构体默认值：默认 GET 方法、根路径、空 body
TEST(RackHttpClient, RequestDefaults)
{
    rack::com::RackHttpRequest req;
    EXPECT_EQ(req.method, rack::com::RackHttpMethod::GET);
    EXPECT_EQ(req.path, "/");
    EXPECT_TRUE(req.body.empty());
    EXPECT_TRUE(req.headers.empty());
    EXPECT_EQ(req.remote_port, -1);
}

// 方法名与枚举互转（rack_http_types.h 中随客户端一并使用的纯逻辑）
TEST(RackHttpClient, MethodStringConversions)
{
    EXPECT_EQ(rack::com::MethodToString(rack::com::RackHttpMethod::GET), "GET");
    EXPECT_EQ(rack::com::MethodToString(rack::com::RackHttpMethod::POST), "POST");
    EXPECT_EQ(rack::com::MethodToString(rack::com::RackHttpMethod::PUT), "PUT");
    EXPECT_EQ(rack::com::MethodToString(rack::com::RackHttpMethod::DELETE_), "DELETE");
    EXPECT_EQ(rack::com::MethodToString(rack::com::RackHttpMethod::PATCH), "PATCH");
    EXPECT_EQ(rack::com::MethodToString(rack::com::RackHttpMethod::OPTIONS), "OPTIONS");

    EXPECT_EQ(rack::com::StringToMethod("GET"), rack::com::RackHttpMethod::GET);
    EXPECT_EQ(rack::com::StringToMethod("POST"), rack::com::RackHttpMethod::POST);
    EXPECT_EQ(rack::com::StringToMethod("PUT"), rack::com::RackHttpMethod::PUT);
    EXPECT_EQ(rack::com::StringToMethod("DELETE"), rack::com::RackHttpMethod::DELETE_);
    EXPECT_EQ(rack::com::StringToMethod("PATCH"), rack::com::RackHttpMethod::PATCH);
    EXPECT_EQ(rack::com::StringToMethod("OPTIONS"), rack::com::RackHttpMethod::OPTIONS);
    // 未知方法名返回 INVALID
    EXPECT_EQ(rack::com::StringToMethod("not-a-method"), rack::com::RackHttpMethod::INVALID);
}
