#include "urma_0385_urma_cmd_create_jetty_grp_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0385UrmaCmdCreateJettyGrpInvalidParam> g_urma("urma_0385");

bool Urma0385UrmaCmdCreateJettyGrpInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0385UrmaCmdCreateJettyGrpInvalidParam::GetName() const
{
    return "urma_cmd_create_jetty_grp 参数非法";
}

std::string Urma0385UrmaCmdCreateJettyGrpInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || jetty_grp == NULL || cfg == "
           "NULL`；该路径返回 -1";
}

RootCause Urma0385UrmaCmdCreateJettyGrpInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0385UrmaCmdCreateJettyGrpInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0385UrmaCmdCreateJettyGrpInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0385UrmaCmdCreateJettyGrpInvalidParam::GetId() const
{
    return "urma_0385";
}
} // namespace diag
