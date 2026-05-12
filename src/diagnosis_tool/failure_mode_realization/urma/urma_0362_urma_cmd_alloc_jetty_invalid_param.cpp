#include "urma_0362_urma_cmd_alloc_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0362UrmaCmdAllocJettyInvalidParam> g_urma("urma_0362");

bool Urma0362UrmaCmdAllocJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0362UrmaCmdAllocJettyInvalidParam::GetName() const
{
    return "urma_cmd_alloc_jetty 参数非法";
}

std::string Urma0362UrmaCmdAllocJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || jetty == NULL || cfg == NULL`；该路径返回 "
           "-1";
}

RootCause Urma0362UrmaCmdAllocJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0362UrmaCmdAllocJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0362UrmaCmdAllocJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0362UrmaCmdAllocJettyInvalidParam::GetId() const
{
    return "urma_0362";
}
} // namespace diag
