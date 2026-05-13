#include "urma_0016_urma_provider_bond_uninit_provider_bond_register_ops_not_regis.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis> g_urma("urma_0016");

bool Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Provider Bond register ops not registered."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis::GetName() const
{
    return "urma_provider_bond_uninit Provider Bond register ops not regis";
}

std::string Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Provider Bond register ops not registered.";
}

std::string Urma0016UrmaProviderBondUninitProviderBondRegisterOpsNotRegis::GetId() const
{
    return "urma_0016";
}
} // namespace diag
