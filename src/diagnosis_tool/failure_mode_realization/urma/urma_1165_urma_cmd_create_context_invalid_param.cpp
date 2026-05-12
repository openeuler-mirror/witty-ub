#include "urma_1165_urma_cmd_create_context_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1165UrmaCmdCreateContextInvalidParam> g_urma("urma_1165");

bool Urma1165UrmaCmdCreateContextInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1165UrmaCmdCreateContextInvalidParam::GetName() const
{
    return "urma_cmd_create_context 参数非法";
}

std::string Urma1165UrmaCmdCreateContextInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败；该路径返回 -1";
}

RootCause Urma1165UrmaCmdCreateContextInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1165UrmaCmdCreateContextInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1165UrmaCmdCreateContextInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1165UrmaCmdCreateContextInvalidParam::GetId() const
{
    return "urma_1165";
}
} // namespace diag
