#include "urma_0379_urma_cmd_bind_jetty_ex_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0379UrmaCmdBindJettyExInvalidParam> g_urma("urma_0379");

bool Urma0379UrmaCmdBindJettyExInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0379UrmaCmdBindJettyExInvalidParam::GetName() const
{
    return "urma_cmd_bind_jetty_ex 参数非法";
}

std::string Urma0379UrmaCmdBindJettyExInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "tjetty == NULL || ex_cfg `；该路径返回 EINVAL";
}

RootCause Urma0379UrmaCmdBindJettyExInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0379UrmaCmdBindJettyExInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0379UrmaCmdBindJettyExInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0379UrmaCmdBindJettyExInvalidParam::GetId() const
{
    return "urma_0379";
}
} // namespace diag
