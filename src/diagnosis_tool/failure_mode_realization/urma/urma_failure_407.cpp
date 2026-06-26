#include "urma_failure_407.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure407> g_urma("urma_407");

bool UrmaFailure407::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure407::GetName() const
{
    return "URMA context、dev_fd、JFC、配置参数无效导致创建JFC失败";
}

std::string UrmaFailure407::GetRootCauseDesc() const
{
    return "urma_cmd_create_jfc用于创建JFC，调用方传入的URMA "
           "context、dev_fd、JFC、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure407::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure407::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure407::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfc，Invalid parameter。";
}

std::string UrmaFailure407::GetId() const
{
    return "urma_407";
}
} // namespace diag
