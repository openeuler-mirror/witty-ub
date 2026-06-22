#include "urma_failure_091.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure091> g_urma("urma_091");

bool UrmaFailure091::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_tp_attr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure091::GetName() const
{
    return "TP、ATTR无效导致获取TP、ATTR失败";
}

std::string UrmaFailure091::GetRootCauseDesc() const
{
    return "urma_cmd_get_tp_attr用于获取TP、ATTR，调用方传入的TP、ATTR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure091::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure091::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure091::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure091::GetId() const
{
    return "urma_091";
}
} // namespace diag
