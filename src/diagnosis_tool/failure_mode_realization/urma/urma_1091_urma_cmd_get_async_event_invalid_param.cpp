#include "urma_1091_urma_cmd_get_async_event_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1091UrmaCmdGetAsyncEventInvalidParam> g_urma("urma_1091");

bool Urma1091UrmaCmdGetAsyncEventInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1091UrmaCmdGetAsyncEventInvalidParam::GetName() const
{
    return "urma_cmd_get_async_event 参数非法";
}

std::string Urma1091UrmaCmdGetAsyncEventInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->async_fd < 0 || event == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1091UrmaCmdGetAsyncEventInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1091UrmaCmdGetAsyncEventInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1091UrmaCmdGetAsyncEventInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1091UrmaCmdGetAsyncEventInvalidParam::GetId() const
{
    return "urma_1091";
}
} // namespace diag
