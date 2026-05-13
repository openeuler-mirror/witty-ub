#include "urma_0070_urma_unregister_provider_ops_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0070UrmaUnregisterProviderOpsInvalidParam> g_urma("urma_0070");

bool Urma0070UrmaUnregisterProviderOpsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0070UrmaUnregisterProviderOpsInvalidParam::GetName() const
{
    return "urma_unregister_provider_ops 参数非法";
}

std::string Urma0070UrmaUnregisterProviderOpsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `provider_ops == NULL || provider_ops->name == NULL`；该路径返回 -1";
}

RootCause Urma0070UrmaUnregisterProviderOpsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0070UrmaUnregisterProviderOpsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0070UrmaUnregisterProviderOpsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0070UrmaUnregisterProviderOpsInvalidParam::GetId() const
{
    return "urma_0070";
}
} // namespace diag
