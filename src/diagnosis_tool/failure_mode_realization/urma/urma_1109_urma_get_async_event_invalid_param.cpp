#include "urma_1109_urma_get_async_event_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1109UrmaGetAsyncEventInvalidParam> g_urma("urma_1109");

bool Urma1109UrmaGetAsyncEventInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1109UrmaGetAsyncEventInvalidParam::GetName() const
{
    return "urma_get_async_event 参数非法";
}

std::string Urma1109UrmaGetAsyncEventInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || event == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1109UrmaGetAsyncEventInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1109UrmaGetAsyncEventInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1109UrmaGetAsyncEventInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1109UrmaGetAsyncEventInvalidParam::GetId() const
{
    return "urma_1109";
}
} // namespace diag
