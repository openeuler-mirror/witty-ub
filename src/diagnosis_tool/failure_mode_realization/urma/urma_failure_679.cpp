#include "urma_failure_679.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure679> g_urma("urma_679");

bool UrmaFailure679::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_set_bonding_mode") != std::string::npos &&
           message.find("Invalid context.") != std::string::npos;
}

std::string UrmaFailure679::GetName() const
{
    return "bonding、MODE状态不满足要求导致设置bonding、MODE失败";
}

std::string UrmaFailure679::GetRootCauseDesc() const
{
    return "bondp_set_bonding_mode执行设置bonding、MODE时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure679::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure679::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure679::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Invalid context.。";
}

std::string UrmaFailure679::GetId() const
{
    return "urma_679";
}
} // namespace diag
