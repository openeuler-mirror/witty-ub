#include "urma_failure_101.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure101> g_urma("urma_101");

bool UrmaFailure101::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty") != std::string::npos &&
           message.find("Failed to delete jetty because it has remote jetty, try unbind first") != std::string::npos;
}

std::string UrmaFailure101::GetName() const
{
    return "下层资源删除失败导致删除Jetty失败";
}

std::string UrmaFailure101::GetRootCauseDesc() const
{
    return "urma_delete_jetty清理Jetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure101::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure101::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure101::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty，Failed to delete jetty because it has remote jetty, "
           "try unb"
           "ind first。";
}

std::string UrmaFailure101::GetId() const
{
    return "urma_101";
}
} // namespace diag
