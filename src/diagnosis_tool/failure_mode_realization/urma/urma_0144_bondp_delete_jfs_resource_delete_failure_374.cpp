#include "urma_0144_bondp_delete_jfs_resource_delete_failure_374.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0144BondpDeleteJfsResourceDeleteFailure374> g_urma("urma_0144");

bool Urma0144BondpDeleteJfsResourceDeleteFailure374::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete jfs[%], still in use. use_cnt: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0144BondpDeleteJfsResourceDeleteFailure374::GetName() const
{
    return "bondp_delete_jfs 删除资源失败（日志行374）";
}

std::string Urma0144BondpDeleteJfsResourceDeleteFailure374::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EAGAIN";
}

RootCause Urma0144BondpDeleteJfsResourceDeleteFailure374::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0144BondpDeleteJfsResourceDeleteFailure374::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0144BondpDeleteJfsResourceDeleteFailure374::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete jfs[%], still in use. use_cnt: %";
}

std::string Urma0144BondpDeleteJfsResourceDeleteFailure374::GetId() const
{
    return "urma_0144";
}
} // namespace diag
