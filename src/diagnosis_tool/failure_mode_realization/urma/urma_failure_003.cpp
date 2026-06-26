#include "urma_failure_003.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure003> g_urma("urma_003");

bool UrmaFailure003::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("init_active_indices") != std::string::npos &&
           message.find("Invalid active port id, value: 0x") != std::string::npos;
}

std::string UrmaFailure003::GetName() const
{
    return "indices状态不满足要求导致初始化indices失败";
}

std::string UrmaFailure003::GetRootCauseDesc() const
{
    return "init_active_indices执行初始化indices时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure003::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure003::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：init_active_indices，Invalid active port id, value: 0x。";
}

std::string UrmaFailure003::GetId() const
{
    return "urma_003";
}
} // namespace diag
