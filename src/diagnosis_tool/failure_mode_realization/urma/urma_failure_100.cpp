#include "urma_failure_100.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure100> g_urma("urma_100");

bool UrmaFailure100::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jetty") != std::string::npos &&
           message.find("Failed to delete jetty because it has remote jetty, try unbind first") != std::string::npos;
}

std::string UrmaFailure100::GetName() const
{
    return "下层资源删除失败导致释放Jetty失败";
}

std::string UrmaFailure100::GetRootCauseDesc() const
{
    return "urma_free_jetty清理Jetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure100::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure100::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure100::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jetty，Failed to delete jetty because it has remote jetty, "
           "try unbin"
           "d first。";
}

std::string UrmaFailure100::GetId() const
{
    return "urma_100";
}
} // namespace diag
