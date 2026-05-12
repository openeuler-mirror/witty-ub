#include "urma_1146_urma_delete_notifier_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1146UrmaDeleteNotifierInvalidParam> g_urma("urma_1146");

bool Urma1146UrmaDeleteNotifierInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1146UrmaDeleteNotifierInvalidParam::GetName() const
{
    return "urma_delete_notifier 参数非法";
}

std::string Urma1146UrmaDeleteNotifierInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `notifier == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1146UrmaDeleteNotifierInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1146UrmaDeleteNotifierInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1146UrmaDeleteNotifierInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1146UrmaDeleteNotifierInvalidParam::GetId() const
{
    return "urma_1146";
}
} // namespace diag
