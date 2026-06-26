#include "urma_failure_038.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure038> g_urma("urma_038");

bool UrmaFailure038::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jetty") != std::string::npos &&
           message.find("failed to init alloc jetty cmd") != std::string::npos;
}

std::string UrmaFailure038::GetName() const
{
    return "Jetty临时结构分配失败导致分配Jetty失败";
}

std::string UrmaFailure038::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jetty执行分配Jetty前需要准备Jetty临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure038::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure038::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure038::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jetty，failed to init alloc jetty cmd。";
}

std::string UrmaFailure038::GetId() const
{
    return "urma_038";
}
} // namespace diag
