#include "urma_failure_673.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure673> g_urma("urma_673");

bool UrmaFailure673::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_user_ctl_set_bonding_mode") != std::string::npos &&
           message.find("Invalid set bonding mode param.") != std::string::npos;
}

std::string UrmaFailure673::GetName() const
{
    return "USER、CTL、bonding状态不满足要求导致设置USER、CTL、bonding失败";
}

std::string UrmaFailure673::GetRootCauseDesc() const
{
    return "bondp_user_ctl_set_bonding_"
           "mode执行设置USER、CTL、bonding时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure673::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure673::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure673::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_set_bonding_mode，Invalid set bonding mode param.。";
}

std::string UrmaFailure673::GetId() const
{
    return "urma_673";
}
} // namespace diag
