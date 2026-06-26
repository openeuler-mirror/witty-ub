#include "urma_failure_128.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure128> g_urma("urma_128");

bool UrmaFailure128::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_tp_attr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure128::GetName() const
{
    return "provider未提供get_tp_list操作实现无效导致设置TP、ATTR失败";
}

std::string UrmaFailure128::GetRootCauseDesc() const
{
    return "urma_set_tp_attr用于设置TP、ATTR，调用方传入的provider未提供get_tp_"
           "list操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure128::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure128::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure128::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure128::GetId() const
{
    return "urma_128";
}
} // namespace diag
