#include "urma_failure_175.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure175> g_urma("urma_175");

bool UrmaFailure175::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure175::GetName() const
{
    return "URMA context、dev_fd、JFS、配置参数无效导致分配JFS失败";
}

std::string UrmaFailure175::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfs用于分配JFS，调用方传入的URMA "
           "context、dev_fd、JFS、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure175::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure175::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure175::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfs，Invalid parameter。";
}

std::string UrmaFailure175::GetId() const
{
    return "urma_175";
}
} // namespace diag
