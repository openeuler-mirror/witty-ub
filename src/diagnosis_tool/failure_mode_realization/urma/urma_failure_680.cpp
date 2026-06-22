#include "urma_failure_680.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure680> g_urma("urma_680");

bool UrmaFailure680::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_set_bonding_mode") != std::string::npos &&
           message.find("Invalid bonding mode:") != std::string::npos;
}

std::string UrmaFailure680::GetName() const
{
    return "bonding、MODE状态不满足要求导致设置bonding、MODE失败";
}

std::string UrmaFailure680::GetRootCauseDesc() const
{
    return "bondp_set_bonding_mode执行设置bonding、MODE时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure680::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure680::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure680::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Invalid bonding mode:。";
}

std::string UrmaFailure680::GetId() const
{
    return "urma_680";
}
} // namespace diag
