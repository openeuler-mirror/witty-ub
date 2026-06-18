#include "urma_failure_088.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure088> g_urma("urma_088");

bool UrmaFailure088::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_tp_attr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure088::GetName() const
{
    return "URMA context、tp_attr无效导致设置TP、ATTR失败";
}

std::string UrmaFailure088::GetRootCauseDesc() const
{
    return "urma_cmd_set_tp_attr用于设置TP、ATTR，调用方传入的URMA "
           "context、tp_attr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure088::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure088::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure088::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure088::GetId() const
{
    return "urma_088";
}
} // namespace diag
