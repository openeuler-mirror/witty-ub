#include "urma_0512_urma_cmd_modify_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0512UrmaCmdModifyJettyInvalidParam> g_urma("urma_0512");

bool Urma0512UrmaCmdModifyJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0512UrmaCmdModifyJettyInvalidParam::GetName() const
{
    return "urma_cmd_modify_jetty 参数非法";
}

std::string Urma0512UrmaCmdModifyJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "attr == NULL`；该路径返回 -1";
}

RootCause Urma0512UrmaCmdModifyJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0512UrmaCmdModifyJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0512UrmaCmdModifyJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0512UrmaCmdModifyJettyInvalidParam::GetId() const
{
    return "urma_0512";
}
} // namespace diag
