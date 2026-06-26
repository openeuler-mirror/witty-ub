#include "urma_failure_662.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure662> g_urma("urma_662");

bool UrmaFailure662::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_validate_driver") != std::string::npos &&
           message.find("Invalid driver name length.") != std::string::npos;
}

std::string UrmaFailure662::GetName() const
{
    return "validate、driver状态不满足要求导致validatevalidate、driver失败";
}

std::string UrmaFailure662::GetRootCauseDesc() const
{
    return "urma_validate_"
           "driver执行validatevalidate、driver时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure662::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure662::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure662::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_validate_driver，Invalid driver name length.。";
}

std::string UrmaFailure662::GetId() const
{
    return "urma_662";
}
} // namespace diag
