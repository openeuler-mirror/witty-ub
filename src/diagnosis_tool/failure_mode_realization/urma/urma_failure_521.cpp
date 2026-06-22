#include "urma_failure_521.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure521> g_urma("urma_521");

bool UrmaFailure521::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_context") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure521::GetName() const
{
    return "context无效导致删除context失败";
}

std::string UrmaFailure521::GetRootCauseDesc() const
{
    return "urma_cmd_delete_context用于删除context，调用方传入的context不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure521::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure521::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure521::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_context，Invalid parameter。";
}

std::string UrmaFailure521::GetId() const
{
    return "urma_521";
}
} // namespace diag
