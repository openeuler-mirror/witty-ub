#include "urma_failure_637.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure637> g_urma("urma_637");

bool UrmaFailure637::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_smac") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure637::GetName() const
{
    return "URMA context、mac无效导致获取SMAC失败";
}

std::string UrmaFailure637::GetRootCauseDesc() const
{
    return "urma_cmd_get_smac用于获取SMAC，调用方传入的URMA context、mac不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure637::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure637::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure637::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_smac，Invalid parameter.。";
}

std::string UrmaFailure637::GetId() const
{
    return "urma_637";
}
} // namespace diag
