#include "urma_1047_bondp_get_async_event_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1047BondpGetAsyncEventInvalidParam> g_urma("urma_1047");

bool Urma1047BondpGetAsyncEventInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1047BondpGetAsyncEventInvalidParam::GetName() const
{
    return "bondp_get_async_event 参数非法";
}

std::string Urma1047BondpGetAsyncEventInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->async_fd < 0 || v_event == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1047BondpGetAsyncEventInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1047BondpGetAsyncEventInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1047BondpGetAsyncEventInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1047BondpGetAsyncEventInvalidParam::GetId() const
{
    return "urma_1047";
}
} // namespace diag
