#include "urma_failure_102.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure102> g_urma("urma_102");

bool UrmaFailure102::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_batch") != std::string::npos &&
           message.find("Failed to delete as jetty has remote jetty, try unbind, index:") != std::string::npos;
}

std::string UrmaFailure102::GetName() const
{
    return "下层资源删除失败导致删除Jetty失败";
}

std::string UrmaFailure102::GetRootCauseDesc() const
{
    return "urma_delete_jetty_batch清理Jetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure102::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure102::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure102::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_batch，Failed to delete as jetty has remote jetty, "
           "try unbin"
           "d, index:。";
}

std::string UrmaFailure102::GetId() const
{
    return "urma_102";
}
} // namespace diag
