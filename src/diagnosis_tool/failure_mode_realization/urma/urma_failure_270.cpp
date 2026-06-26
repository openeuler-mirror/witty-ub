#include "urma_failure_270.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure270> g_urma("urma_270");

bool UrmaFailure270::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_eid_by_ip") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure270::GetName() const
{
    return "provider未提供get_tp_attr操作实现无效导致获取EID、IP失败";
}

std::string UrmaFailure270::GetRootCauseDesc() const
{
    return "urma_get_eid_by_ip用于获取EID、IP，调用方传入的provider未提供get_tp_"
           "attr操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure270::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure270::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure270::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_eid_by_ip，Invalid parameter.。";
}

std::string UrmaFailure270::GetId() const
{
    return "urma_270";
}
} // namespace diag
