#include "urma_0014_urma_provider_bond_init_provider_bond_register_ops_failed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed> g_urma("urma_0014");

bool Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Provider Bond register ops failed."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed::GetName() const
{
    return "urma_provider_bond_init Provider Bond register ops failed.";
}

std::string Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Provider Bond register ops failed.";
}

std::string Urma0014UrmaProviderBondInitProviderBondRegisterOpsFailed::GetId() const
{
    return "urma_0014";
}
} // namespace diag
