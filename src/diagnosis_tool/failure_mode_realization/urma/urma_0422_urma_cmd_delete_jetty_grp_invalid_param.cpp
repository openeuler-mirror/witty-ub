#include "urma_0422_urma_cmd_delete_jetty_grp_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0422UrmaCmdDeleteJettyGrpInvalidParam> g_urma("urma_0422");

bool Urma0422UrmaCmdDeleteJettyGrpInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0422UrmaCmdDeleteJettyGrpInvalidParam::GetName() const
{
    return "urma_cmd_delete_jetty_grp 参数非法";
}

std::string Urma0422UrmaCmdDeleteJettyGrpInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty_grp == NULL || jetty_grp->urma_ctx == NULL || "
           "jetty_grp->urma_ctx->dev_fd < 0`；该路径返回 -1";
}

RootCause Urma0422UrmaCmdDeleteJettyGrpInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0422UrmaCmdDeleteJettyGrpInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0422UrmaCmdDeleteJettyGrpInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0422UrmaCmdDeleteJettyGrpInvalidParam::GetId() const
{
    return "urma_0422";
}
} // namespace diag
