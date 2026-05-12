#include "urma_0883_urma_rearm_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0883UrmaRearmJfcInvalidParam> g_urma("urma_0883");

bool Urma0883UrmaRearmJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0883UrmaRearmJfcInvalidParam::GetName() const
{
    return "urma_rearm_jfc 参数非法";
}

std::string Urma0883UrmaRearmJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->rearm_jfc == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0883UrmaRearmJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0883UrmaRearmJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0883UrmaRearmJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0883UrmaRearmJfcInvalidParam::GetId() const
{
    return "urma_0883";
}
} // namespace diag
