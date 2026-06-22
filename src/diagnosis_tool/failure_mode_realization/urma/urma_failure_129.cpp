#include "urma_failure_129.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure129> g_urma("urma_129");

bool UrmaFailure129::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_tp_attr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure129::GetName() const
{
    return "URMA context、tp_attr_cnt、tp_attr_bitmap、tp_attr无效导致获取TP、ATTR失败";
}

std::string UrmaFailure129::GetRootCauseDesc() const
{
    return "urma_get_tp_attr用于获取TP、ATTR，调用方传入的URMA "
           "context、tp_attr_cnt、tp_attr_bitmap、tp_attr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure129::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure129::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure129::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure129::GetId() const
{
    return "urma_129";
}
} // namespace diag
