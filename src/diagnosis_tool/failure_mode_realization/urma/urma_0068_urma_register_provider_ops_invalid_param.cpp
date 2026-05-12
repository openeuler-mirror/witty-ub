#include "urma_0068_urma_register_provider_ops_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0068UrmaRegisterProviderOpsInvalidParam> g_urma("urma_0068");

bool Urma0068UrmaRegisterProviderOpsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0068UrmaRegisterProviderOpsInvalidParam::GetName() const
{
    return "urma_register_provider_ops 参数非法";
}

std::string Urma0068UrmaRegisterProviderOpsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `provider_ops == NULL || provider_ops->name == NULL`；该路径返回 -1";
}

RootCause Urma0068UrmaRegisterProviderOpsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0068UrmaRegisterProviderOpsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0068UrmaRegisterProviderOpsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0068UrmaRegisterProviderOpsInvalidParam::GetId() const
{
    return "urma_0068";
}
} // namespace diag
