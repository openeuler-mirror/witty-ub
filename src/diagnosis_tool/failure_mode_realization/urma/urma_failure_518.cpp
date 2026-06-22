#include "urma_failure_518.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure518> g_urma("urma_518");

bool UrmaFailure518::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_context") != std::string::npos &&
           message.find("Failed to delete pcontext") != std::string::npos;
}

std::string UrmaFailure518::GetName() const
{
    return "下层资源删除失败导致删除context失败";
}

std::string UrmaFailure518::GetRootCauseDesc() const
{
    return "bondp_delete_context清理context时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure518::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure518::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure518::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_context，Failed to delete pcontext。";
}

std::string UrmaFailure518::GetId() const
{
    return "urma_518";
}
} // namespace diag
