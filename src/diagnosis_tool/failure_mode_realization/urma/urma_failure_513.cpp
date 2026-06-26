#include "urma_failure_513.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure513> g_urma("urma_513");

bool UrmaFailure513::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jetty") != std::string::npos &&
           message.find("Failed to delete pjetty") != std::string::npos;
}

std::string UrmaFailure513::GetName() const
{
    return "下层资源删除失败导致删除Jetty失败";
}

std::string UrmaFailure513::GetRootCauseDesc() const
{
    return "bondp_delete_jetty清理Jetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure513::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure513::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure513::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jetty，Failed to delete pjetty。";
}

std::string UrmaFailure513::GetId() const
{
    return "urma_513";
}
} // namespace diag
