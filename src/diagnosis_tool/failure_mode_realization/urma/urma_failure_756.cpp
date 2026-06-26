#include "urma_failure_756.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure756> g_urma("urma_756");

bool UrmaFailure756::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_context_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure756::GetName() const
{
    return "URMA context、URMA设备、provider操作表无效导致设置context失败";
}

std::string UrmaFailure756::GetRootCauseDesc() const
{
    return "urma_set_context_opt用于设置context，调用方传入的URMA "
           "context、URMA设备、provider操作表不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure756::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure756::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure756::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_context_opt，Invalid parameter.。";
}

std::string UrmaFailure756::GetId() const
{
    return "urma_756";
}
} // namespace diag
