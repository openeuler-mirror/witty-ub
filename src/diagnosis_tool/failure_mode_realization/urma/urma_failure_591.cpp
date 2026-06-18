#include "urma_failure_591.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure591> g_urma("urma_591");

bool UrmaFailure591::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_batch") != std::string::npos &&
           message.find("Failed to alloc memory.") != std::string::npos;
}

std::string UrmaFailure591::GetName() const
{
    return "urma context *分配失败导致删除Jetty失败";
}

std::string UrmaFailure591::GetRootCauseDesc() const
{
    return "urma_delete_jetty_batch执行删除Jetty前需要准备urma context *，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure591::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure591::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure591::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_batch，Failed to alloc memory.。";
}

std::string UrmaFailure591::GetId() const
{
    return "urma_591";
}
} // namespace diag
