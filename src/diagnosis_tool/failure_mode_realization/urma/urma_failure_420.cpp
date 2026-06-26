#include "urma_failure_420.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure420> g_urma("urma_420");

bool UrmaFailure420::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure420::GetName() const
{
    return "URMA context、dev_fd、JFC、配置参数无效导致分配JFC失败";
}

std::string UrmaFailure420::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfc用于分配JFC，调用方传入的URMA "
           "context、dev_fd、JFC、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure420::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure420::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure420::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfc，Invalid parameter。";
}

std::string UrmaFailure420::GetId() const
{
    return "urma_420";
}
} // namespace diag
