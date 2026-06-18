#include "urma_failure_672.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure672> g_urma("urma_672");

bool UrmaFailure672::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_user_ctl_set_bonding_mode_legacy") != std::string::npos &&
           message.find("Invalid aggr mode:") != std::string::npos;
}

std::string UrmaFailure672::GetName() const
{
    return "USER、CTL、bonding状态不满足要求导致设置USER、CTL、bonding失败";
}

std::string UrmaFailure672::GetRootCauseDesc() const
{
    return "bondp_user_ctl_set_bonding_mode_"
           "legacy执行设置USER、CTL、bonding时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure672::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure672::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure672::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_set_bonding_mode_legacy，Invalid aggr mode:。";
}

std::string UrmaFailure672::GetId() const
{
    return "urma_672";
}
} // namespace diag
