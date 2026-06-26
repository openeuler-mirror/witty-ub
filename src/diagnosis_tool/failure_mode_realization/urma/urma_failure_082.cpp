#include "urma_failure_082.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure082> g_urma("urma_082");

bool UrmaFailure082::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_modify_tp") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure082::GetName() const
{
    return "URMA context、dev_fd、配置参数、属性参数无效导致修改TP失败";
}

std::string UrmaFailure082::GetRootCauseDesc() const
{
    return "urma_cmd_modify_tp用于修改TP，调用方传入的URMA "
           "context、dev_fd、配置参数、属性参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure082::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure082::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure082::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_tp，Invalid parameter.。";
}

std::string UrmaFailure082::GetId() const
{
    return "urma_082";
}
} // namespace diag
