#include "urma_failure_272.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure272> g_urma("urma_272");

bool UrmaFailure272::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_smac") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure272::GetName() const
{
    return "provider未提供get_ip_by_eid操作实现无效导致获取SMAC失败";
}

std::string UrmaFailure272::GetRootCauseDesc() const
{
    return "urma_get_smac用于获取SMAC，调用方传入的provider未提供get_ip_by_"
           "eid操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure272::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure272::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure272::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_smac，Invalid parameter.。";
}

std::string UrmaFailure272::GetId() const
{
    return "urma_272";
}
} // namespace diag
