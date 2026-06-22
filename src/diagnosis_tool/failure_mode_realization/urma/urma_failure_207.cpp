#include "urma_failure_207.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure207> g_urma("urma_207");

bool UrmaFailure207::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jetty") != std::string::npos &&
           message.find("alloc_jetty failed.") != std::string::npos;
}

std::string UrmaFailure207::GetName() const
{
    return "Jetty临时结构分配失败导致分配Jetty失败";
}

std::string UrmaFailure207::GetRootCauseDesc() const
{
    return "urma_alloc_jetty执行分配Jetty前需要准备Jetty临时结构，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure207::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure207::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure207::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jetty，alloc_jetty failed.。";
}

std::string UrmaFailure207::GetId() const
{
    return "urma_207";
}
} // namespace diag
