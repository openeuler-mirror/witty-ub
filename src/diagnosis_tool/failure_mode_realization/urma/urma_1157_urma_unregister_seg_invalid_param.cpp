#include "urma_1157_urma_unregister_seg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1157UrmaUnregisterSegInvalidParam> g_urma("urma_1157");

bool Urma1157UrmaUnregisterSegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1157UrmaUnregisterSegInvalidParam::GetName() const
{
    return "urma_unregister_seg 参数非法";
}

std::string Urma1157UrmaUnregisterSegInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `target_seg == NULL || target_seg->urma_ctx == NULL || "
           "target_seg->urma_ctx->dev == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1157UrmaUnregisterSegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1157UrmaUnregisterSegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1157UrmaUnregisterSegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1157UrmaUnregisterSegInvalidParam::GetId() const
{
    return "urma_1157";
}
} // namespace diag
