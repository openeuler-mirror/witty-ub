#include "urma_0901_urma_create_notifier_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0901UrmaCreateNotifierInvalidParam> g_urma("urma_0901");

bool Urma0901UrmaCreateNotifierInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0901UrmaCreateNotifierInvalidParam::GetName() const
{
    return "urma_create_notifier 参数非法";
}

std::string Urma0901UrmaCreateNotifierInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL`；该路径返回 NULL";
}

RootCause Urma0901UrmaCreateNotifierInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0901UrmaCreateNotifierInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0901UrmaCreateNotifierInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0901UrmaCreateNotifierInvalidParam::GetId() const
{
    return "urma_0901";
}
} // namespace diag
