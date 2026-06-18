#include "urma_failure_601.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure601> g_urma("urma_601");

bool UrmaFailure601::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_grp") != std::string::npos &&
           message.find("delete_jetty_grp failed.") != std::string::npos;
}

std::string UrmaFailure601::GetName() const
{
    return "下层资源删除失败导致创建Jetty组失败";
}

std::string UrmaFailure601::GetRootCauseDesc() const
{
    return "urma_create_jetty_grp清理Jetty组时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure601::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure601::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure601::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_grp，delete_jetty_grp failed.。";
}

std::string UrmaFailure601::GetId() const
{
    return "urma_601";
}
} // namespace diag
